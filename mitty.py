#!/usr/bin/env python3

from utils.fire import FireProx
import argparse, requests, concurrent.futures, time, threading,sys
from collections import defaultdict
from tqdm import tqdm

### Globals ###
target_url = None
aws_key = None
aws_secret = None
aws_region = None

### Colors ###
reset = '\033[0m'
lightred = '\033[91m'
blue = '\033[34m'
lightgreen = '\033[92m'
gold = '\033[33m'

def arg_parser():
    # Import globals and regions comparison table
    global target_repo, aws_key, aws_secret, aws_region
    regions = [
			"us-east-2", "us-east-1","us-west-1","us-west-2","eu-west-3",
			"ap-northeast-1","ap-northeast-2","ap-south-1",
			"ap-southeast-1","ap-southeast-2","ca-central-1",
			"eu-central-1","eu-west-1","eu-west-2","sa-east-1",
		]

    parser = argparse.ArgumentParser(prog="Mitty", description="A command-line tool for brute-forcing commit IDs via FireProx.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-t", "--repository", type=str, required=False, help="The target GitHub repository in the format \"USER/REPO\" (e.g., e-nzym3/mitty)")
    parser.add_argument("-k", "--key", type=str, required=True, help="AWS key for FireProx")
    parser.add_argument("-s", "--secret", type = str, required = True, help = "AWS secret key for FireProx")
    parser.add_argument("-r", "--region", type = str, required = False, default = "us-east-1", help = "AWS region to deploy gateways in (default = us-east-1)")
    parser.add_argument("-n", "--count", type = int, required = False, default = 5, help = "Number of concurrent streams use (default = 5)")
    parser.add_argument("-c", "--cleanup", action = "store_true", default = False, help = "Cleanup APIs from AWS")

    # Process args to appropriate global variables
    args = parser.parse_args()
    target_repo = f"https://github.com/{args.repository}"
    aws_key = args.key
    aws_secret = args.secret

    if args.region not in regions:
        print(f"{lightred}[!] Supplied region \"{args.region}\" is not valid! Please select one of the following:")
        print(", ".join(regions))
        print(f"{reset}")
    else:
        aws_region = args.region
    
    if args.cleanup == False and not args.repository:
        parser.error(f"{lightred}[!] --repository is required if --cleanup is not set")

    return args


def fireprox_args(command, url, api_id = None):
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
    return { "api_gateway_id" : resource_id, "proxy_url" : proxy_url, "region" : region }

def load_apis(region, url, count):
    apis = []
    print(f"{blue}[*] Generating API Gateways:{reset}")
    for x in range(count):
        apis.append(create_api(region, url.strip()))
        print(f"[+] Created API Gateway in {region} ID: {apis[x]['api_gateway_id']} - {lightgreen}{apis[x]['proxy_url']} => {url}{reset}")
    return apis


def destroy_apis(region):
    print(f"{blue}[*] Destroying APIs:{reset}")
    args, helpstr = fireprox_args("list", region)
    fp = FireProx(args, helpstr)
    active_apis = fp.list_api()
    
    pbar = tqdm(total=len(active_apis), desc="Destroying APIs", unit = " apis", position=0, leave=True)
    for a in active_apis:
        result = fp.delete_api(a['id'])
        success = 'Success!' if result else 'Failed!'
        tqdm.write(f'{lightgreen}[+] Destroying {a["id"]} => {success}{reset}')
        pbar.update(1)


def request_handler(count):
    global target_repo
    results = defaultdict(list)
    lock = threading.Lock()

    ## Create API gateways for requests
    apis = load_apis(aws_region, target_repo, count)

    ## Total number of 4-character hex combinations for commit SHA-1 hashes
    total_combinations = 0x10000
    
    ## Calculate the size of each bucket
    bucket_size = total_combinations // count
    remainder = total_combinations % count

    ## Initialize the list of buckets
    buckets = []
    start = 0

    for i in range(count):
        # Calculate the end of the current bucket
        end = start + bucket_size + (1 if i < remainder else 0)
        
        # Create a bucket with hex strings
        bucket = [f'{j:04x}' for j in range(start, end)]
        buckets.append(bucket)
        
        # Move to the next bucket
        start = end
    print(f"\n{blue}[*] Starting Brute Force:{reset}")
    pbar = tqdm(total=total_combinations, unit=" requests", desc="Checking Commits", position=0, leave=True)

    ## Generate HTTP requests through each "api" through multithreading for each bucket
    def fetch_data(api, bucket):
        for commit_hash in bucket:
            url = f"{api['proxy_url']}commit/{commit_hash}"
            try:
                response = requests.get(url)
                with lock:  # Acquire the lock before writing to the results dictionary
                    results[commit_hash].append(response.status_code)
                    if response.status_code == 200:
                        tqdm.write(f"{gold}[+] Commit Found: {target_repo}/commit/{commit_hash}{reset}")
            except requests.exceptions.RequestException as e:
                with lock:  # Acquire the lock before writing to the results dictionary
                    results[commit_hash].append(f"Error: {str(e)}")
            pbar.update(1)

    # Using ThreadPoolExecutor to manage concurrent threads
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Start a new thread for each API and its corresponding bucket
        futures = [executor.submit(fetch_data, api, bucket) for api, bucket in zip(apis, buckets)]

        # Wait for all threads to complete
        concurrent.futures.wait(futures)

    return results


if __name__ == "__main__":
    print("                                                                                                    ")
    print("                                                       @@@@     @@@@                                ")
    print("               @@@@@@@@       @@@@@                 @@@@@@@@@@@@@@@@@@@@                            ")
    print("           @@@@@@@@@@@@@@@@@@@@@@@@@@%           @@@@@.....:%@@#.....=@@@@@@@@@@@@@@@ @@@@@@@@      ")
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
    print("                                                                             @@@@@@%%%@@@@          ")
    print("                                                                               @@@@@@@@@@           ")
    print()
    print("                                        Mitty - by E-nzym3 (https://github.com/e-nzym3)             ")
    print(f"\n{blue}[*] Starting Mitty...{reset}\n")
    args = arg_parser()
    if args.cleanup: 
        destroy_apis(aws_region)
    else:
        request_handler(args.count)