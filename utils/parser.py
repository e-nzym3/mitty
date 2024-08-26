from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import sys

# Colors
gold = "\033[33m"
lightred = "\033[91m"
reset = "\033[0m"
blue = "\033[34m"


def get_driver():
    """
    Initialize and return a WebDriver instance based on browser availability.

    :return: A WebDriver instance for Chrome or Firefox.
    """
    try:
        # Attempt to initialize Chrome WebDriver
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=chrome_options,
        )
        # print("Chrome browser found and will be used.")
        return driver

    except Exception as chrome_exception:
        print(f"{lightred}[!] Chrome initialization failed: {chrome_exception}{reset}")

        try:
            # If Chrome initialization fails, attempt to initialize Firefox WebDriver
            firefox_options = FirefoxOptions()
            firefox_options.add_argument("--headless")
            driver = webdriver.Firefox(
                service=FirefoxService(GeckoDriverManager().install()),
                options=firefox_options,
            )
            # print("Firefox browser found and will be used.")
            return driver

        except Exception as firefox_exception:
            print(
                f"{lightred}[!] Firefox initialization failed: {firefox_exception}{reset}"
            )

    # Raise an error if neither browser is found
    raise RuntimeError(
        f"{lightred} [!] Neither Chrome nor Firefox browsers could be initialized. Please install one to proceed.{reset}"
    )


def parser(repo, hashes, log_file):

    with open(f"{log_file}_parsed", "w") as wf:
        wf.write("Commit,Type\n")
        try:
            # Initialize the WebDriver based on available browser
            driver = get_driver()

            for hash in hashes:
                url = f"https://github.com/{repo}/commit/{hash}"
                # Navigate to the URL
                driver.get(url)

                try:
                    # Locate the <div> element with id "spoof-warning"
                    div_element = driver.find_element(By.ID, "spoof-warning")

                    # Check if the "hidden" and "aria-hidden" attributes are present
                    # fmt: off
                    if div_element.get_attribute("hidden") is not None and div_element.get_attribute("aria-hidden") is not None:
                        wf.write(f'{url},regular\n')
                    else:
                        wf.write(f'{url},deleted/dereferenced\n')
                        print(f"{gold}[+] Deleted commit found: {url}{reset}")

                except Exception as e:
                    print(
                        f"{lightred} [!] An error occurred while checking the element: {e}{reset}"
                    )
                    # fmt: on
            # Clean up and close the browser
            driver.quit()
            print(f"\n{blue}[*] Parsing results written to: {log_file+'.parsed'}{reset}\n")  # fmt: skip

        except RuntimeError as e:
            print(e)
            sys.exit(1)  # Exit the script with an error code


def selenium_test(url):
    print(f"{blue}[*] Testing Selenium:{reset}")

    try:
        driver = get_driver()
        driver.get(url)
        driver.quit()
    except Exception as e:
        print(f"{lightred}[!] Error: {str(e)}{reset}")
        sys.exit(1)
