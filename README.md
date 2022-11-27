# Intelgram
[![version](https://img.shields.io/github/v/release/martinkovacs/intelgram?color=orange)](https://github.com/martinkovacs/intelgram/releases)
[![python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://img.shields.io/badge/python-%3E%3D3.10-blue)
[![license](https://img.shields.io/github/license/martinkovacs/intelgram?color=brightgreen)](LICENSE)

OSINT tool for Instagram. This project is a modern rewrite of [Osintgram](https://github.com/Datalux/Osintgram)

## Features:
- Works with 2FA
- Works on public and followed private profiles
- I/O intensive tasks run on multiple threads

## Installation
Requires `python >= 3.10`

1. Clone this repo: `git clone https://github.com/martinkovacs/intelgram.git`
2. Enter directory: `cd intelgram`
3. Create a virtual environment: `python3 -m venv venv`
4. Load the virtual environment:
    - Linux: `source venv/bin/activate`
    - Windows: `.\venv\Scripts\activate.ps1`
5. Install dependencies: `pip install -r requirements.txt`
6. Run main.py:
    - As an interactive prompt: `python3 main.py <target username>`
    - Or execute command: `python3 main.py <target username> --command <command>`

## Docker
Requirements: `docker`

1. Download image: `docker pull martinkovacs/intelgram`
2. Run image: `docker run --rm -it -v "$PWD/output:/app/output" martinkovacs/intelgram <target>`

### With docker-compose
Requirements: `docker`, `docker-compose`

1. Clone this repo: `git clone https://github.com/martinkovacs/intelgram.git`
2. Enter directory: `cd intelgram`
3. Run docker-compose: `docker-compose run intelgram <target>`

## Commands
```
- cookies                 (meta) Delete cookies
- exit                    (meta) Exit program
- list                    (meta) Show all commands
- captions                Get the caption of target's posts
- comments                Get the comments on target's posts
- followers               List target's followers
- followers-subset        Find common followers between target and target2
- followings              List target's followings
- followings-subset       Find common followings between target and target2
- hashtags                Get hashtags on target's posts
- highlights              Download target's highlights
- info                    Get target info (only JSON)
- info-list               Get user infos from a .json file
- likers                  Get likers on target's posts
- likes                   Get like data on target's posts
- locations               Get tagged locations on target's posts
- posts                   Download target's posts
- posts-data              Save target's posts data (only JSON)
- posts-tagged            Download posts where the target is tagged
- posts-tagged-data       Save target's tagged posts data (only JSON)
- profile-pic             Download target's profile picture
- stories                 Download target's stories
- tagged                  Get tagged users on target's posts
- tagged-target           Get users that tagged target
- tagged-with             Get users who are tagged on the same posts as target
- target                  Change target
- viewcount               Get target's viewcount
```
