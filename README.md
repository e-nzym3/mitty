# mitty
<p align="center">
  <img src="./logo.png" width="50%">
  <br>
  <b>Github Commit Hash Bruteforce Utility</b>
</p>
<hr>

Mitty is a utility that bruteforces Github's commit hash (the 4-character format). Based on a [Truffle Security](https://trufflesecurity.com/blog/anyone-can-access-deleted-and-private-repo-data-github) article, it is possible to access dereferenced commits for a repository as long as you know the commit hash. Github commits can be accessed by using the first 4 characters of a commit hash (e.g., https://github.com/e-nzym3/mitty/commit/a3fc). As such, the utility focuses on performing 65,536 requests which cover the whole hex character space for a 4-character string (0000 -> ffff).
<br>
<br>
Since Github will prevent excessive consecutive connections from a single IP source, Mitty is designed to utilize [FireProx](https://github.com/ustayready/fireprox), a utility created for automating deployment of AWS API Gateways through which web requests can be proxied. AWS API Gateways will assign a different source IP for each generated request, allowing us to easily rotate our source IP, bypassing the Github protections.
<br>
<br>
<b>Note: the tool does require an AWS Console account. The API Gateways will usually be free unless you end up sending million+ requests</b> ([Gateway API Pricing Page](https://aws.amazon.com/api-gateway/pricing/)).
# Credits
- [knavesec](https://github.com/knavesec) - Most of the FireProx interaction code is based on [CredMaster](https://github.com/knavesec/CredMaster)'s functionality. Also snagged some README blog info.
- ChatGPT and Amazon Q - obviously...
- Microsoft Designer AI - logo

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
If you do not have an AWS account, create one as you will need it for configuring FireProx. Also, follow this [blog](https://bond-o.medium.com/aws-pass-through-proxy-84f1f7fa4b4b) if you do not know how to create AWS keys for FireProx.
<br><br>
Once you have the AWS <b>Access Key</b> and <b>Secret Access key</b>, then you can proceed to using this tool.
# Usage

```console
usage: Mitty [-h] [-t REPOSITORY] -k KEY -s SECRET [-r REGION] [-n COUNT] [-c]

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
                        Number of concurrent streams use (default = 1)
  -c, --cleanup         Cleanup APIs from AWS (in case you had to force close the program)
```

Using "CTRL+C" during execution will initiate a prompt for automatic destruction of all API Gateways. If you force close the script, you can use `-c` to clean-up the gateways afterwards.

<br>
<i>To Do: Add logic to exclude/include commits to forks and to differentiate between dereferenced and normal commits</i>

## Logging
Logging is configured manually within the script and will execute upon closing of each thread. The log file will be created within the current directory. Name of the log file will be in the format of `out_mitty_<target-repo>_<date>.log`.

## Examples
### Starting Brute Force
```console
./mitty -k "AIKAxxxxxxxxxxxxxxxx" -s "xxxxxxxxxxxxxxxxxxxxxxxx" -r us-east-1 -n 10 -t "e-nzym3/mitty"
```
### Cleaning up API Gateways
Use this in case the program crashed, or you force-closed it and did not have a chance to clean up the gateways.
```console
./mitty -k "AIKAxxxxxxxxxxxxxxxx" -s "xxxxxxxxxxxxxxxxxxxxxxxx" -c -r us-east-1
```
**DISCLAIMER: MITTY WILL REMOVE ALL API GATEWAYS FROM SPECIFIED REGION. MAKE SURE YOU DO NOT HAVE ANY IMPORTANT GATEWAYS ON YOUR ACCOUNT!!!**

# To Do List
- Clean-up Code Formatting
- Clean-up Fire.py to only include logic that's required
- Add logic to exclude or include fork commits
- Add logic to check for pre-existing API gateways and re-use them if needed. If not enough pre-existing ones exist, create n of them until they match the required number.
- Add logic to check for various strings within responses.