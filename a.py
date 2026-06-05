import asyncio
import os
import random
from playwright.async_api import async_playwright, Page, BrowserContext

async def simulate_activity(page: Page):
    """Simulates varied human-like activity to prevent idle timeouts and detection."""
    try:
        action = random.choice(["scroll", "mouse_move", "key_nudge", "hover"])
        
        if action == "scroll":
            # Simulate "reading" with multiple small scrolls
            for _ in range(random.randint(2, 5)):
                direction = 1 if random.random() > 0.3 else -1 # 70% chance to scroll down
                amount = random.randint(100, 300) * direction
                await page.mouse.wheel(0, amount)
                await asyncio.sleep(random.uniform(0.2, 0.8))
            print("  [Keep-Alive] Performed reading scrolls.")

        elif action == "mouse_move":
            # Move mouse across several points to mimic looking at different cells
            for _ in range(random.randint(2, 4)):
                x, y = random.randint(100, 1200), random.randint(100, 800)
                # Using more steps for a slower, more human-like path
                await page.mouse.move(x, y, steps=random.randint(15, 30))
                await asyncio.sleep(random.uniform(0.1, 0.5))
            print(f"  [Keep-Alive] Mouse journey completed.")

        elif action == "key_nudge":
            # Pressing a modifier key is a very strong "user is present" signal
            key = random.choice(["Shift", "Control", "Alt"])
            await page.keyboard.down(key)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.keyboard.up(key)
            print(f"  [Keep-Alive] Keyboard nudge: {key} key.")

        elif action == "hover":
            # Try to hover over common editor elements if they exist
            selectors = [".jp-Notebook", "button", "a", ".cm-content"]
            target = random.choice(selectors)
            try:
                element = await page.query_selector(target)
                if element:
                    await element.hover()
                    print(f"  [Keep-Alive] Hovered over {target}.")
            except:
                pass

    except Exception as e:
        print(f"  [Keep-Alive] Warning: Could not simulate activity: {e}")

async def open_kaggle_notebook_and_wait(url: str, wait_hours: int = 5, user_data_dir: str = "./kaggle_profile"):
    """
    Opens Kaggle with persistent cookies and periodic activity simulation.
    """
    # Ensure the profile directory exists
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)

    try:
        async with async_playwright() as p:
            print("Launching browser...")
            
            # Using persistent context to save cookies, session, and login state
            context: BrowserContext = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                ignore_default_args=["--enable-automation"],
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--enable-webgl",
                    "--window-position=0,0",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )

            page: Page = context.pages[0] if context.pages else await context.new_page()
            
            # Advanced Stealth: Mask fingerprinting vectors
            await page.add_init_script("""
                (() => {
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                    window.chrome = { runtime: {} };
                })();
            """)
            
            # Handle console logs for debugging remote site behavior
            page.on("console", lambda msg: print(f"Browser Console: {msg.text}") if msg.type == "error" else None)

            print(f"Navigating to: {url}")
            # Using 'load' instead of 'domcontentloaded' to ensure main assets are parsed
            await page.goto(url, wait_until="load", timeout=120000)
            
            # Detect specific states: Login, Captcha, or Workspace
            content = await page.content()
            if "sign in" in content.lower() or "login" in page.url:
                print("  [Action Required] Session expired or not logged in. Please log in manually.")
            elif "unusual activity" in content.lower() or "captcha" in content.lower():
                print("  [Action Required] Bot detection/Captcha triggered. Please solve it manually.")
            
            # Wait for a key editor element to appear (the notebook container)
            try:
                # Expanded selector list for different Kaggle editor versions
                await page.wait_for_selector(
                    "div[data-test='notebook-editor'], .workweek-workspace, .kj-editor, .jp-Notebook", 
                    timeout=45000
                )
                print("  [Verified] Kaggle editor environment detected.")
            except:
                # If the main editor selector isn't found, it might be in a different state.
                # We'll still try to find the 'Run All' button later, but log a warning.
                print("  [Warning] Editor selector not found. Checking for 'Draft' or 'Viewer' mode...")
                if await page.query_selector("div[text='Edit']"):
                    print("  [Suggestion] Click the 'Edit' button in the browser UI to open the workspace.")
                await page.wait_for_timeout(15000)

            # --- New functionality: Scroll to and click 'Run All' button ---
            print("  [Action] Attempting to find and click 'Run All' button...")
            try:
                # Kaggle often uses divs for buttons. Searching by text is the most robust way.
                # We use .first to ensure we target the primary interaction element.
                run_all_button = page.get_by_text("Run All", exact=True).first
                
                # Wait for the element to be visible. 'enabled' is not a valid state for wait_for.
                await run_all_button.wait_for(state="visible", timeout=30000)
                await run_all_button.scroll_into_view_if_needed()
                print("  [Action] 'Run All' button scrolled into view.")
                print("  [Action] Waiting for 30 seconds before clicking 'Run All'...")
                await asyncio.sleep(30) # Explicit 30-second wait as requested
                await run_all_button.click()
                print("  [Action] 'Run All' button clicked.")
            except Exception as e:
                print(f"  [Warning] Could not find or click 'Run All' button: {e}")

            print(f"Successfully opened {url}.")
            print(f"Waiting for {wait_hours} hours before entering indefinite hold...")
            print(f"Note: Cookies and session are being saved to '{user_data_dir}'.")

            # Periodic activity loop
            total_seconds = wait_hours * 3600
            elapsed = 0

            while elapsed < total_seconds:
                await simulate_activity(page)
                # Randomize interval slightly (approx 5 mins)
                interval = random.randint(240, 360)
                await asyncio.sleep(interval)
                elapsed += interval
                if elapsed % 1800 == 0:  # Log every 30 mins
                    print(f"  [Status] {elapsed / 3600:.1f} hours elapsed...")

            print(f"Initial {wait_hours} hours wait complete. Session will now remain open indefinitely.")

            while True:
                await simulate_activity(page)
                await asyncio.sleep(random.randint(500, 700)) 

    except asyncio.CancelledError:
        print("Script interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Script process ending. If the browser closed, it is because the context was destroyed.")

if __name__ == "__main__":
    KAGGLE_NOTEBOOK_URL = "https://www.kaggle.com/code/decididi/khan-battt/edit"
    WAIT_DURATION_HOURS = 5
    asyncio.run(open_kaggle_notebook_and_wait(KAGGLE_NOTEBOOK_URL, WAIT_DURATION_HOURS))
