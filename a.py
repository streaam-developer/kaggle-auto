import asyncio
import os
import random
from playwright.async_api import async_playwright, Page, BrowserContext

async def simulate_activity(page: Page):
    """Simulates human-like activity to prevent idle timeouts and detection."""
    try:
        # Random scroll
        scroll_amount = random.randint(50, 150)
        await page.mouse.wheel(0, scroll_amount)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        await page.mouse.wheel(0, -scroll_amount)
        
        # Random mouse movement
        x, y = random.randint(100, 700), random.randint(100, 500)
        await page.mouse.move(x, y, steps=10)
        
        print(f"  [Keep-Alive] Activity simulated at {x}, {y}")
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
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                ignore_default_args=["--enable-automation"],
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars"
                ]
            )

            page: Page = context.pages[0] if context.pages else await context.new_page()
            
            # Stealth: Mask the webdriver property
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Handle console logs for debugging remote site behavior
            page.on("console", lambda msg: print(f"Browser Console: {msg.text}") if msg.type == "error" else None)

            print(f"Navigating to: {url}")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Check if we are in the editor or need to log in
            if "login" in page.url:
                print("  [Action Required] Please log in to Kaggle in the browser window.")
            
            # Give Kaggle time to load the actual notebook editor
            await page.wait_for_timeout(10000)

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
