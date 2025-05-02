# Introduction
This script automatically disables WireGuard on OPNsense when a specific website responds with an HTTP 200 (healthy) status.  
The goal is to minimize external port exposure and avoid using SSH or VPN (WireGuard) for remote access.

In setups where internal resources are accessed through specific applications (e.g., code-server from Coder), a VPN is unnecessary.

\* This project is designed for self-hosters, not for enterprise environments.

## Information
- Container runs with internal UID and GID: `1000:1000`
- You can also configure **Mattermost** alert notifications via environment variables.

## Requirements
- Docker and the Docker Compose plugin installed
- OPNsense API key created

### Create OPNsense API Key(Only for WireGuard control)
1. Open OPNsense web ui 
2. Go to `System` > `Access` > `Users`
3. Click `+` button for create User
4. Enter a `username`
5. Enable `Scrambled Password`
6. Select `Privileges`
    - `Status: Services`
    - `VPN: WireGuard`
7. Save
8. Click API create button(`Create and download API key for this user`)

## How to use
### 1. Get Repository
```bash
git clone https://github.com/rolestack/adow.git
cd auto-disable-opnsense-wireguard
```

### 2. Create Docker secret files
- **API_KEY**: (secret path is referenced in `docker-compose.yaml`)
- **API_SECRET**: (secret path is referenced in `docker-compose.yaml`)

### 3. Configuration
- `.env` (see `env.example` for reference)

### 4. Run container
```bash
docker compose up -d
```

## Manual Enable/Disable
The `vpn` file in the repository is a Bash script.  
This script uses an encrypted API key.
```
eval $(gpg --quiet --batch --decrypt .vpn/creds.gpg 2>/dev/null)
```

### How to Create Encrypted API Key

1. Create the `.vpn/creds.txt` file
```plaintext
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here
```

2. Encrypt the file
```bash
gpg --symmetric --cipher-algo AES256 -o .vpn/creds.gpg .vpn/creds.txt
```

3. Delete the original plain text file
```bash
rm .vpn/creds.txt
```