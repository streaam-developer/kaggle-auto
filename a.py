import asyncio
from playwright.async_api import async_playwright, Page, Browser

async def open_kaggle_notebook_and_wait(url: str, wait_hours: int = 5):
    """
    Opens a specified Kaggle notebook URL, waits for a given duration,
    and then keeps the browser session open indefinitely.

    Args:
        url (str): The URL of the Kaggle notebook to open.
        wait_hours (int): The number of hours to wait before entering
                          an indefinite hold state.
    """
    browser: Browser = None # Initialize browser to None for finally block
    try:
        async with async_playwright() as p:
            print("Launching browser...")
            # Launch Chromium in non-headless mode to keep the UI visible
            # You might want to add 'headless=True' if you don't need a visible UI
            # and are running this on a server.
            browser = await p.chromium.launch(headless=False)
            page: Page = await browser.new_page()

            print(f"Navigating to: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            print("Page loaded. Waiting for potential redirects or dynamic content.")

            # Give it a moment for any initial page rendering or redirects to settle
            await page.wait_for_timeout(5000) # Wait for 5 seconds

            print(f"Successfully opened {url}.")
            print(f"Waiting for {wait_hours} hours before entering indefinite hold...")

            # Calculate wait time in milliseconds
            wait_milliseconds = wait_hours * 60 * 60 * 1000
            await page.wait_for_timeout(wait_milliseconds)

            print(f"Initial {wait_hours} hours wait complete. Session will now remain open indefinitely.")
            print("To close the session, stop this script manually (e.g., Ctrl+C).")

            # Keep the script running indefinitely to prevent the browser from closing
            # This loop will effectively pause the script until interrupted.
            while True:
                await asyncio.sleep(3600) # Sleep for an hour, then check again (keeps the event loop alive)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # IMPORTANT: We are intentionally NOT closing the browser here
        # as per the requirement "don't close sessions".
        # If you wanted to close it after the script finishes, you would add:
        # if browser:
        #     await browser.close()
        print("Script finished or interrupted. Browser session might still be active if not manually closed.")

if __name__ == "__main__":
    KAGGLE_NOTEBOOK_URL = "https://www.kaggle.com/code/decididi/khan-battt/edit"
    WAIT_DURATION_HOURS = 5
    asyncio.run(open_kaggle_notebook_and_wait(KAGGLE_NOTEBOOK_URL, WAIT_DURATION_HOURS))
