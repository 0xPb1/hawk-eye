from rich.console import Console
from rich.table import Table
import json, requests, argparse, yaml, re, datetime, os, subprocess, platform, hashlib
from tinydb import TinyDB, Query

# Create a TinyDB instance for storing previous alert hashes
db = TinyDB('previous_alerts.json')

parser = argparse.ArgumentParser(description='🦅 A powerful scanner to scan your Filesystem, S3, MySQL, PostgreSQL, MongoDB, Redis, Google Cloud Storage and Firebase storage for PII and sensitive data.')
parser.add_argument('--connection', action='store', help='YAML Connection file path')
parser.add_argument('--fingerprint', action='store', help='Override YAML fingerprint file path')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
parser.add_argument('--shutup', action='store_true', help='Suppress the Hawk Eye banner 🫣', default=False)

args, extra_args = parser.parse_known_args()


console = Console()

def calculate_msg_hash(msg):
    return hashlib.sha256(msg.encode()).hexdigest()

def print_info(message):
    console.print(f"[yellow][INFO][/yellow] {message}")

def print_debug(message):
    if args.debug:
        console.print(f"[blue][DEBUG][/blue] {message}")

def print_error(message):
    console.print(f"[bold red]❌ {message}")

def print_success(message):
    console.print(f"[bold green]✅ {message}")

def print_info(message):
    console.print(f"[yellow][INFO][/yellow] {message}")
def print_alert(message):
    console.print(f"[bold red][ALERT][/bold red] {message}")

def get_file_owner(file_path):
    owner_name = ""

    # Determine the current operating system
    system = platform.system()

    if system == "Windows":
        try:
            # Run the 'dir /q' command and capture its output
            result = subprocess.check_output(['dir', '/q', file_path], shell=True, text=True)
            # Extract the line containing the file information
            lines = result.splitlines()
            file_name = os.path.basename(file_path)
            if len(lines) >= 6:
                for line in lines:
                    if file_name in line:
                        exploded_line = line.split(' ')
                        owner_name = exploded_line[-2]
        except subprocess.CalledProcessError as e:
            owner_name = ""
    else:
        try:
            from pwd import getpwuid
            # Use the 'os.stat()' method to get the file owner on non-Windows systems
            file_stat = os.stat(file_path)
            owner_name = file_stat.st_uid  # You can also use pwd.getpwuid(file_stat.st_uid).pw_name to get the username
            owner_name = getpwuid(owner_name).pw_name + " (" + str(owner_name) + ")"
        except OSError as e:
            owner_name = ""

    return owner_name

def RedactData(input_string):
    if len(input_string) < 3:
        return input_string

    # Calculate the number of characters to redact in the middle (half of the length)
    redact_count = len(input_string) // 2

    # Split the input string into two parts: before and after the middle
    middle_start = len(input_string) // 2 - redact_count // 2
    middle_end = len(input_string) // 2 + redact_count // 2

    before_middle = input_string[:middle_start]
    middle = input_string[middle_start:middle_end]
    after_middle = input_string[middle_end:]

    # Redact the middle part
    redacted_middle = "*" * len(middle)

    # Concatenate the parts back together
    redacted_string = before_middle + redacted_middle + after_middle

    return redacted_string

def get_connection():
    if args.connection:
        if os.path.exists(args.connection):
            with open(args.connection, 'r') as file:
                connections = yaml.safe_load(file)
                return connections
        else:
            print_error(f"Connection file not found: {args.connection}")
            exit(1)
    else:
        print_error(f"Please provide a connection file using --connection flag")
        exit(1)

def get_fingerprint_file():
    if args.fingerprint:
        if os.path.exists(args.fingerprint):
            with open(args.fingerprint, 'r') as file:
                return yaml.safe_load(file)
        else:
            print_error(f"Fingerprint file not found: {args.fingerprint}")
            exit(1)
    else:
        file_path = "https://github.com/rohitcoder/hawk-eye/raw/main/fingerprint.yml"
        try:
            response = requests.get(file_path, timeout=10)
            print_info(f"Downloading default fingerprint.yml from {file_path}")
            if response.status_code == 200:
                with open('fingerprint.yml', 'wb') as file:
                    file.write(response.content)
                return yaml.safe_load(response.content)
            else:
                print_error(f"Unable to download default fingerprint.yml please provide your own fingerprint file using --fingerprint flag")
                exit(1)
        except Exception as e:
            print_error(f"Unable to download default fingerprint.yml please provide your own fingerprint file using --fingerprint flag")
            exit(1)

patterns = get_fingerprint_file()

def print_banner():
    banner = r"""
                                /T /I
                                / |/ | .-~/
                            T\ Y  I  |/  /  _
            /T               | \I  |  I  Y.-~/
            I l   /I       T\ |  |  l  |  T  /
        T\ |  \ Y l  /T   | \I  l   \ `  l Y
    __  | \l   \l  \I l __l  l   \   `  _. |
    \ ~-l  `\   `\  \  \\ ~\  \   `. .-~   |
    \   ~-. "-.  `  \  ^._ ^. "-.  /  \   |
    .--~-._  ~-  `  _  ~-_.-"-." ._ /._ ." ./
    >--.  ~-.   ._  ~>-"    "\\   7   7   ]
    ^.___~"--._    ~-{  .-~ .  `\ Y . /    |
    <__ ~"-.  ~       /_/   \   \I  Y   : |
    ^-.__           ~(_/   \   >._:   | l______
        ^--.,___.-~"  /_/   !  `-.~"--l_ /     ~"-.                 + ================================================== +
                (_/ .  ~(   /'     "~"--,Y   -=b-. _)               + [bold yellow]H[/bold yellow].[bold yellow]A[/bold yellow].[bold yellow]W[/bold yellow].[bold yellow]K[/bold yellow] [bold yellow]Eye[/bold yellow] - [bold blue]Highly Advanced Watchful Keeper Eye[/bold blue] +
                (_/ .  \  :           / l      c"~o \               + ================================================== +
                    \ /    `.    .     .^   \_.-~"~--.  )                 
                    (_/ .   `  /     /       !       )/                   Hunt for Secrets & PII Data, like never before!
                    / / _.   '.   .':      /        '                           A Tool by [bold red]Rohit Kumar (@rohitcoder)[/bold red]
                    ~(_/ .   /    _  `  .-<_                                    
                        /_/ . ' .-~" `.  / \  \          ,z=.
                        ~( /   '  :   | K   "-.~-.______//
                        "-,.    l   I/ \_______{--->._(=====.
                        //(     \  <                  \\
                        /' /\     \  \                 \\
                        .^. / /\     "  }__ //===--`\\
                    / / ' '  "-.,__ {---(==-
                    .^ '       :  T  ~"   ll       
                    / .  .  . : | :!        \\
                (_/  /   | | j-"             ~^~^
                    ~-<_(_.^-~"
    """
    if not args.shutup:
        console.print(banner)

connections = get_connection()

def match_strings(content):
    matched_strings = []

    if 'notify' in connections:
        redacted: bool = connections.get('notify', {}).get('redacted', False)

    for pattern_name, pattern_regex in patterns.items():
        print_debug(f"Matching pattern: {pattern_name}")
        found = {} 
        ## parse pattern_regex as Regex
        complied_regex = re.compile(pattern_regex, re.IGNORECASE)
        print_debug(f"Regex: {complied_regex}")
        print_debug(f"Content: {content}")
        matches = re.findall(complied_regex, content)
        print_debug(f"Matches: {matches}")
        if matches:
            print_debug(f"Found {len(matches)} matches for pattern: {pattern_name}")
            found['pattern_name'] = pattern_name
            redacted_matches = []
            if redacted:
                print_debug(f"Redacting matches for pattern: {pattern_name}")
                for match in matches:
                    print_debug(f"Redacting match: {match}")
                    redacted_matches.append(RedactData(match))
                found['matches'] = redacted_matches
            else:
                found['matches'] = matches

            if redacted:
                found['sample_text'] = RedactData(content[:50])
            else:
                found['sample_text'] = content[:50]
            
            matched_strings.append(found)
    print_debug(f"Matched strings: {matched_strings}")
    return matched_strings

def should_exclude_file(file_name, exclude_patterns):
    _, extension = os.path.splitext(file_name)
    if extension in exclude_patterns:
        print_debug(f"Excluding file: {file_name} because of extension: {extension}")
        return True
    
    for pattern in exclude_patterns:
        if pattern in file_name:
            print_debug(f"Excluding file: {file_name} because of pattern: {pattern}")
            return True
    return False

def should_exclude_folder(folder_name, exclude_patterns):
    for pattern in exclude_patterns:
        if pattern in folder_name:
            return True
    return False

def list_all_files_iteratively(path, exclude_patterns):
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if not should_exclude_folder(os.path.join(root, d), exclude_patterns)]

        for file in files:
            if not should_exclude_file(file, exclude_patterns):
                yield os.path.join(root, file)

def read_match_strings(file_path, source):
    print_info(f"Scanning file: {file_path}")
    content = ''
    try:
        with open(file_path, 'r', encoding="utf-8") as file:
            content = file.read()
    except Exception as e:
        pass
    matched_strings = match_strings(content)
    return matched_strings

def getFileData(file_path):
    try:
        # Get file metadata
        file_stat = os.stat(file_path)

        # Get the username of the file's creator (Windows)
        creator_name = get_file_owner(file_path)
        # Convert timestamps to human-readable format
        created_time = datetime.datetime.fromtimestamp(file_stat.st_ctime)
        modified_time = datetime.datetime.fromtimestamp(file_stat.st_mtime)

        # Create a dictionary with the file information
        ## should be dict
        file_info = {
            "creator": creator_name,
            "created_time": created_time.strftime("%Y-%m-%d %H:%M:%S"),
            "modified_time": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return file_info

    except FileNotFoundError:
        return json.dumps({"error": "File not found"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def SlackNotify(msg):
    if 'notify' in connections:
        notify_config = connections['notify']
        # Check if suppress_duplicates is set to True
        suppress_duplicates = notify_config.get('suppress_duplicates', False)
        
        if suppress_duplicates:
            # Calculate the hash of the message
            msg_hash = calculate_msg_hash(msg)
            
            # Check if the message hash already exists in the previous alerts database
            Alert = Query()
            if db.contains(Alert.msg_hash == msg_hash):
                print_debug("Duplicate message detected. Skipping webhook trigger.")
                return
        
        slack_config = notify_config.get('slack', {})
        webhook_url = slack_config.get('webhook_url', '')
        
        if webhook_url != '':
            try:
                payload = {
                    'text': msg,
                }
                headers = {'Content-Type': 'application/json'}
                requests.post(webhook_url, data=json.dumps(payload), headers=headers)
                
                if suppress_duplicates:
                    # Store the message hash in the previous alerts database
                    db.insert({'msg_hash': msg_hash})
            except Exception as e:
                print_error(f"An error occurred: {str(e)}")
