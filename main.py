import inteltk
from inteltk.colors import *

from intelgram.intelgram import Intelgram
from intelgram.logo import ascii_logo
from intelgram.colors import *

parser = inteltk.create_parser(ascii_logo)
parser.add_argument("target", help="Target's username")
parser.add_argument("-c", "--command", help="Run command directly, without interaction", metavar="command", action="append")
parser.add_argument("-e", "--extra-input", help="Add extra inputs for commands which ask the user", metavar="input", action="append")
parser.add_argument("-i", "--interactive", help="Force interactive mode", action="store_true")
parser.add_argument("-j", "--json", help="Save output to .json", action="store_true")
parser.add_argument("-o", "--output", help="Output directory", metavar="output_dir", action="store")
parser.add_argument("-s", "--style", help="Set a valid PrettyTable style (only for txt exports)", metavar="style", action="store")
parser.add_argument("-t", "--txt", help="Save output to .txt", action="store_true")
parser.add_argument("-v", "--verification-code", help="Set the 2fa code", metavar="code", action="store")

args = parser.parse_args()
client = Intelgram(*vars(args).values())

COMMANDS = {
    "captions": {
        "func": client.captions,
        "desc": "\t\tGet the caption of target's posts"
    },
    "comments": {
        "func": client.comments,
        "desc": "\t\tGet the comments on target's posts"
    },
    "followers": {
        "func": client.followers,
        "desc": "\t\tList target's followers"
    },
    "followers-subset": {
        "func": client.followers_subset,
        "desc": "\tFind common followers between target and target2"
    },
    "followings": {
        "func": client.followings,
        "desc": "\t\tList target's followings"
    },
    "followings-subset": {
        "func": client.followings_subset,
        "desc": "\tFind common followings between target and target2"
    },
    "hashtags": {
        "func": client.hashtags,
        "desc": "\t\tGet hashtags on target's posts"
    },
    "highlights": {
        "func": client.highlights,
        "desc": "\t\tDownload target's highlights"
    },
    "info": {
        "func": client.info,
        "desc": "\t\t\tGet target info (only JSON)",
    },
    "info-list": {
        "func": client.info_list,
        "desc": "\t\tGet user infos from a .json file"
    },
    "likers": {
        "func": client.likers,
        "desc": "\t\t\tGet likers on target's posts"
    },
    "likes": {
        "func": client.likes,
        "desc": "\t\t\tGet like data on target's posts",
    },
    "locations": {
        "func": client.locations,
        "desc": "\t\tGet tagged locations on target's posts",
    },
    "posts": {
        "func": client.posts,
        "desc": "\t\t\tDownload target's posts"
    },
    "posts-data": {
        "func": client.posts_data,
        "desc": "\t\tSave target's posts data (only JSON)"
    },
    "posts-tagged": {
        "func": client.posts_tagged,
        "desc": "\t\tDownload posts where the target is tagged"
    },
    "posts-tagged-data": {
        "func": client.posts_tagged_data,
        "desc": "\tSave target's tagged posts data (only JSON)"
    },
    "profile-pic": {
        "func": client.profile_pic,
        "desc": "\t\tDownload target's profile picture"
    },
    "stories": {
        "func": client.stories,
        "desc": "\t\t\tDownload target's stories"
    },
    "tagged": {
        "func": client.tagged,
        "desc": "\t\t\tGet tagged users on target's posts"
    },
    "tagged-target": {
        "func": client.tagged_target,
        "desc": "\t\tGet users that tagged target"
    },
    "tagged-with": {
        "func": client.tagged_with,
        "desc": "\t\tGet users who are tagged on the same posts as target"
    },
    "target": {
        "func": client.target,
        "desc": "\t\t\tChange target",
    },
    "viewcount": {
        "func": client.viewcount,
        "desc": "\t\tGet target's viewcount",
    }
}

itk = inteltk.IntelTk(COMMANDS, client.settings_path)
COMMANDS = itk.COMMANDS


def main() -> None:
    inteltk.set_exit_program(itk._exit_program)

    if client.interactive:
        inteltk.set_readline(itk._completer)
        inteltk.startup(ascii_logo, "1.0", "An Instagram OSINT tool", client.json, client.txt)
    
    while True:
        command = (args.command[0] if args.command else inputcolor("Run a command: ", CYAN)).lower()

        match command:
            case "json=y":
                client.json = True
                printcolor(f"JSON output {GREEN}enabled", BLUE)
            case "json=n":
                client.json = False
                printcolor(f"JSON output {RED}disabled", BLUE)
            case "txt=y":
                client.txt = True
                printcolor(f"TXT output {GREEN}enabled", BLUE)
            case "txt=n":
                client.txt = False
                printcolor(f"TXT output {RED}disabled", BLUE)
            case _:
                if command in COMMANDS:
                    COMMANDS[command]["func"]()
                else:
                    printcolor("Invalid command", RED)

        if args.command:
            args.command.pop(0)
            if not args.command:
                break


if __name__ == "__main__":
    main()
