# mitty
<p align="center">
  <img src="./logo.png" width="50%">
  <br>
  <b>Github Commit Hash Bruteforce Utility</b><br>
  <a href="https://enzym3.io/introducing-mitty/">Blog Post</a>
</p>
<hr>

Mitty is a utility that bruteforces Github's commit hash (the 4-character format). Based on a [Truffle Security](https://trufflesecurity.com/blog/anyone-can-access-deleted-and-private-repo-data-github) article, it is possible to access dereferenced commits for a repository as long as you know the commit hash. Github commits can be accessed by using the first 4 characters of a commit hash (e.g., https://github.com/e-nzym3/mitty/commit/a3fc). As such, the utility focuses on performing 65,536 requests which cover the whole hex character space for a 4-character string (0000 -> ffff).
<br>
<br>
Since Github will prevent excessive consecutive connections from a single IP source, Mitty is designed to utilize [FireProx](https://github.com/ustayready/fireprox), a utility created for automating deployment of AWS API Gateways through which web requests can be proxied. AWS API Gateways will assign a different source IP for each generated request, allowing us to easily rotate our source IP, bypassing the Github protections.
<br>
<br>
<b>Note: the tool does require an AWS Console account. The API Gateways will usually be free unless you end up sending million+ requests</b> ([Gateway API Pricing Page](https://aws.amazon.com/api-gateway/pricing/)).

# Features
- Find commits by bruteforcing the commit hash.
- Flag found commits that match a word-based filter.
- Parse results to determine if the found commit has been deleted or not.

# Credits
- [knavesec](https://github.com/knavesec) - Most of the FireProx interaction code is based on [CredMaster](https://github.com/knavesec/CredMaster)'s functionality. Also snagged some README blog info.

# Installation
Clone Repo:
```console
git clone https://github.com/e-nzym3/mitty
```
Install Python dependencies:
```console
cd mitty
sudo python3 -m pip install -r requirements.txt
```
You can also do it through `pipenv` if you prefer.
# Config
If you do not have an AWS account, create one as you will need it for standing up API Gateways via Mitty. You can follow my [blog post](https://enzym3.io/introducing-mitty/) for instructions on how to achieve this.
<br><br>
Once you have the AWS <b>Access Key</b> and <b>Secret Access key</b>, then you can proceed to using this tool.
# Usage

```console
usage: Mitty [-h] [-t REPOSITORY] -k KEY -s SECRET [-r REGION] [-n COUNT] [-c] [-m MATCH] [-p]

A command-line tool for brute-forcing commit IDs via FireProx.

options:
  -h, --help            show this help message and exit
  -t REPOSITORY, --repository REPOSITORY
                        The target GitHub repository in the format "USER/REPO" (e.g., e-nzym3/mitty)
  -k KEY, --key KEY     AWS key for FireProx
  -s SECRET, --secret SECRET
                        AWS secret key for FireProx
  -r REGION, --region REGION
                        AWS region to deploy gateways in (default = us-east-1)
  -n COUNT, --count COUNT
                        Number of concurrent streams use (default = 5)
  -c, --cleanup         Cleanup APIs from AWS
  -m MATCH, --match MATCH
                        Comma separated list of words to look for in commit pages (e.g., "key,secret,password")
  -p, --parse           Parse found commits to check which were deleted
```

The script will automatically kill all API Gateways on your account in the provided region once it terminates successfully. Also, using "CTRL+C" during execution will initiate an automatic destruction of all API Gateways. If you force close the script for whatever reason, you can use `-c` to clean-up the gateways afterwards.
<br><br>
The word match function works on regex basis and is case insensitive. It searches through the "body" HTML element of the Github Commit page. As such, keep in mind that there may be some matches that occur on parameters within the raw HTML doc, not just text that is rendered on the screen.

## Logging
Logging is configured manually within the script and will execute upon closing of each thread. The log file will be created within the current directory. Name of the log file will be in the format of `out_mitty_<target-repo>_<date>.log`.
<br><br>
The parsing log file will have the same name as above, but will end in `_parsed`.

## Parsing
The parsing feature utilizes Selenium to determine whether the found commit has been deleted or not. This is simply because of how Github decides to mark these commits as such. Github uses JavaScript to render the "" alert, so Selenium is required to have each commit page rendered appropriately and then checked for presence of the message.
<br><br>
Selenium can be pretty buggy so I included the "--selenium-test" argument to test your configuration by having it run on "https://google.com". This may run a while, especially with timeout issues. So be patient.

## Examples
### Starting a Standard Brute Force
```console
./mitty -k "AIKAxxxxxxxxxxxxxxxx" -s "xxxxxxxxxxxxxxxxxxxxxxxx" -r us-east-1 -n 10 -t "e-nzym3/mitty"
```

### Conducting a Brute Force with a Word Match and Parsing
```console
./mitty.py -k "AIKAxxxxxxxxxxxxxxxx" -s "xxxxxxxxxxxxxxxxxxxxxxxx" -n 10 -t "e-nzym3/mitty" -m "password" -p
```

### Cleaning up API Gateways
Use this in case the program crashed, or you force-closed it and did not have a chance to clean up the gateways.
```console
./mitty -k "AIKAxxxxxxxxxxxxxxxx" -s "xxxxxxxxxxxxxxxxxxxxxxxx" -c -r us-east-1
```
**DISCLAIMER: MITTY WILL REMOVE ALL API GATEWAYS FROM SPECIFIED REGION. MAKE SURE YOU DO NOT HAVE ANY IMPORTANT GATEWAYS ON YOUR ACCOUNT!!!**

# To Do List
- Clean-up Fire.py to only include logic that's required
- Add logic to check for pre-existing API gateways and re-use them if needed. If not enough pre-existing ones exist, create n of them until they match the required number.