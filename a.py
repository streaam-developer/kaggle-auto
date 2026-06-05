import asyncio
import os
import random
from playwright.async_api import async_playwright, Page, BrowserContext

async def simulate_activity(page: Page):
    """Simulates varied human-like activity to prevent idle timeouts and detection."""
    try:
        action = random.choice(["scroll", "mouse_move", "key_nudge", "hover"])
        
        if action == "scroll":
            # Pehle mouse ko center mein move karein taaki sahi container target ho
            await page.mouse.move(683, 384)
            for _ in range(random.randint(2, 5)):
                direction = 1 if random.random() > 0.3 else -1 # 70% chance to scroll down
                amount = random.randint(200, 500) * direction
                
                # Deep Scroll: Ye script window aur Kaggle ke internal containers dono ko scroll karegi
                await page.evaluate(f"""(amt) => {{
                    window.scrollBy(0, amt);
                    const selectors = ['.jp-Notebook', '.workweek-workspace', '.kj-editor', '[role="main"]', '.editor-container'];
                    selectors.forEach(s => {{
                        const el = document.querySelector(s);
                        if (el) el.scrollBy(0, amt);
                    }});
                    // Fallback: Agar upar waale kaam na karein toh jo bhi scrollable div hai use scroll karo
                    document.querySelectorAll('div').forEach(d => {{
                        if (d.scrollHeight > d.clientHeight) d.scrollBy(0, amt);
                    }});
                }}""", amount)
                await asyncio.sleep(random.uniform(0.2, 0.8))
            print("  [Keep-Alive] Performed reading scrolls.")

        elif action == "mouse_move":
            # Move mouse across several points to mimic looking at different cells
            for _ in range(random.randint(2, 4)):
                x, y = random.randint(100, 1300), random.randint(100, 700)
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
                viewport={'width': 1366, 'height': 768},
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

            # --- New functionality: Handle "Restart & Clear Cell Outputs" if in Draft mode ---
            print("  [Action] Checking for 'Restart & Clear Cell Outputs' button (Draft mode)...")
            try:
                # Use a robust selector for the "Restart & Clear Cell Outputs" button.
                # Based on the provided HTML snippet, it's a <p> tag with specific text.
                restart_clear_button = page.get_by_text("Restart & Clear Cell Outputs", exact=True).first
                
                # Wait for the element to be visible and enabled
                await restart_clear_button.wait_for(state="visible", timeout=10000)
                await restart_clear_button.wait_for(state="enabled", timeout=5000) # Check if it's clickable
                await restart_clear_button.scroll_into_view_if_needed()
                print("  [Action] 'Restart & Clear Cell Outputs' button found and scrolled into view.")
                await restart_clear_button.click()
                print("  [Action] 'Restart & Clear Cell Outputs' button clicked. Waiting for notebook to stabilize...")
                await asyncio.sleep(10) # Give some time for the action to process
            except Exception as e:
                print(f"  [Info] 'Restart & Clear Cell Outputs' button not found or not clickable (likely not in Draft mode or already clear): {e}")

            # --- New functionality: Scroll to and click 'Run All' button ---
            print("  [Action] Attempting to find and click 'Run All' button...")
            try:
                run_all_button = page.get_by_text("Run All", exact=True).first
                
                # Wait for visibility and then force scroll to center
                await run_all_button.wait_for(state="visible", timeout=45000)
                
                # Forceful scrolling logic
                await run_all_button.scroll_into_view_if_needed()
                await run_all_button.evaluate("el => el.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'center' })")
                
                print("  [Action] 'Run All' button centered in view.")
                print("  [Action] Waiting for 30 seconds before clicking 'Run All'...")
                await asyncio.sleep(30) # Explicit 30-second wait as requested
                await run_all_button.click()
                print("  [Action] 'Run All' button clicked.")
            except Exception as e:
                print(f"  [Warning] Could not find or click 'Run All' button: {e}")

            print(f"Successfully opened {url}.")
            print(f"--- Starting Advanced Execution Monitoring ---")
            print(f"Script will now keep the code running and handle disconnections.")
            start_time = asyncio.get_event_loop().time()
            last_activity_time = 0

            while True:
                try:
                    # 1. Live Log Extraction (Har loop mein check karega)
                    current_logs = await page.evaluate("""() => {
                        // Kaggle outputs are usually in these classes
                        const outputDivs = document.querySelectorAll('.jp-OutputArea-output, .kj-output-area');
                        return Array.from(outputDivs).map(div => div.innerText).join('\\n');
                    }""")
                    
                    log_lines = [line for line in current_logs.splitlines() if line.strip()]
                    
                    # Terminal Clear karke last 100 lines dikhana
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"=== KAGGLE LIVE LOGS (Last 100 Lines) | Runtime: {(asyncio.get_event_loop().time() - start_time)/3600:.2f}h ===")
                    print("-" * 60)
                    for line in log_lines[-100:]:
                        print(line)
                    print("-" * 60)
                    print("  [Monitor] Monitoring for disconnections and system popups...")

                    # 2. Advanced Session Guard (Reconnect & Auto-Run)
                    # Check and click common popups
                    for action_text in ["Reconnect", "Dismiss", "Stay", "Wait", "Close"]:
                        btn = page.get_by_text(action_text, exact=False).first
                        if await btn.is_visible():
                            print(f"  [Monitor] System popup detected. Clicking '{action_text}'...")
                            await btn.click()
                            await asyncio.sleep(5)

                    # Check if Execution has stopped
                    run_all_btn = page.get_by_text("Run All", exact=True).first
                    if await run_all_btn.is_visible():
                        print("  [Monitor] Execution stopped or kernel idle. Re-triggering 'Run All'...")
                        await run_all_btn.evaluate("el => el.scrollIntoView({ behavior: 'auto', block: 'center' })")
                        await asyncio.sleep(2)
                        await run_all_btn.click()

                    # 3. Simulate Human Activity (Throttled: Har 5-7 mins mein ek baar)
                    now = asyncio.get_event_loop().time()
                    if now - last_activity_time > random.randint(300, 450):
                        await simulate_activity(page)
                        last_activity_time = now

                except Exception as monitor_err:
                    print(f"  [Warning] Monitor Loop encountered an error: {monitor_err}")
                    pass

                # loop interval ko chota kiya hai taaki logs live update hon
                # Anti-detection ke liye sleep time aur activity throttled hai
                await asyncio.sleep(20) 

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
