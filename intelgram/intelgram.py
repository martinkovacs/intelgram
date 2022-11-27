from __future__ import annotations
import concurrent.futures
import json
import os
import re
import sys
import time
from typing import Any
import urllib.request

import geopy.geocoders
import instagrapi
from instagrapi.exceptions import (
    ClientError,
    TwoFactorRequired,
    UnknownError,
    UserNotFound
)
from inteltk import calculate_remaining_time
from inteltk.colors import *
import prettytable

from intelgram.logger import setup_logger


class Intelgram:
    def __init__(self, name: str, command: list[str], extra_input: list[str], interactive: bool,
            json: bool, output: str, style: str, txt: bool, verification_code: str) -> None:
        setup_logger()
        
        self.client = instagrapi.Client()
        
        self.target_name = name
        self.extra_input = extra_input
        self.interactive = interactive or not command
        self.json = json
        self.txt = txt
        self.table_style = eval(f"prettytable.{style}") if style else prettytable.DEFAULT
        self.output = output or "output"
        os.makedirs(self.output, exist_ok=True)
        self.verification_code = verification_code

        self.credentials_path = "config/credentials.json"
        self.settings_path = "config/settings.json"
        self.username, self.password = self._get_credentials().values()

        self._login()
        printcolor(f"Logged in as {WHITE}{self.client.username} {BLUE}[{self.client.user_id}]", GREEN)
        self._print_target()

    def captions(self) -> None:
        captions = self._get_captions()

        if not captions:
            printcolor("No captions found", RED)
            return

        table = prettytable.PrettyTable()
        table.field_names = ["id", "taken_at", "caption"]
        table.max_width["caption"] = 50
        table.add_rows([[*caption.values()] for caption in captions])
        
        print(table.get_string())
        printcolor(f"Found {len(captions)} captions", GREEN)

        data = [dict(caption.items()) for caption in captions]
        self._save_to_files(data, table, "captions")
        
    def comments(self) -> None:
        posts = self._get_user_medias()

        table = prettytable.PrettyTable()
        table.field_names = ["id", "comment_pk", "user_pk", "username", "created_at", "like_count", "text"]
        table.max_width["text"] = 50

        if self.json:
            data = {}

        comments = self._get_comments_threaded(posts)

        post_count = 0
        comment_count = 0
        for post in comments:
            for comment in post[1]:
                table.add_row([
                    post[0], comment["pk"], comment["user"]["pk"], comment["user"]["username"],
                    comment["created_at_utc"], comment["like_count"], comment["text"]
                ])
                comment_count += 1
            if self.json:
                data[post[0]] = post[1]
            post_count += 1

        if comment_count == 0:
            printcolor("No comments found", RED)
            return

        print(table.get_string())
        printcolor(f"Found {post_count} post with comments. Total comments: {comment_count}", GREEN)

        self._save_to_files(data, table, "comments")

    def followers(self) -> None:
        followers = self._get_user_followers()

        table = prettytable.PrettyTable()
        table.field_names = ["pk", "username", "full_name"]

        if self.json:
            data = []

        for user in followers:
            table.add_row([user["pk"], user["username"], user["full_name"]])

            if self.json:
                data.append(user)

        print(table.get_string())
        printcolor(f"Found {len(followers)} followers", GREEN)

        self._save_to_files(data, table, "followers")
    
    def followers_subset(self) -> None:
        followers = self._get_user_followers()
        
        if not (target2 := self.parse_extra_input()):
            if self.interactive:
                target2 = inputcolor("Enter second target username: ", CYAN)
            else:
                printcolor("No target2 given!", RED)
        
        try:
            target2_id = self.client.user_id_from_username(target2)
        except UserNotFound as e:
            printcolor(f"Error: {e.message}", RED)
            return
        
        followers2 = self._get_user_followers(target2_id)

        table = prettytable.PrettyTable()
        table.field_names = ["pk", "username", "full_name"]

        if self.json:
            data = []

        subset = [user for user in followers if user in followers2]
        for user in subset:
            table.add_row([user["pk"], user["username"], user["full_name"]])
            
            if self.json:
                data.append(user)

        print(table.get_string())
        printcolor(f"Found {len(subset)} common followers", GREEN)

        self._save_to_files(data, table, f"followers-subset_{target2}", f"and {target2} followers subset")
        
    def followings(self) -> None:
        followings = self._get_user_followings()

        table = prettytable.PrettyTable()
        table.field_names = ["pk", "username", "full_name"]

        if self.json:
            data = []

        for user in followings:
            table.add_row([user["pk"], user["username"], user["full_name"]])

            if self.json:
                data.append(user)

        print(table.get_string())
        printcolor(f"Found {len(followings)} followings", GREEN)

        self._save_to_files(data, table, "followings")
        
    def followings_subset(self) -> None:
        followings = self._get_user_followings()
        
        if not (target2 := self.parse_extra_input()):
            if self.interactive:
                target2 = inputcolor("Enter second target username: ", CYAN)
            else:
                printcolor("No target2 given!")
        
        try:
            target2_id = self.client.user_id_from_username(target2)
        except UserNotFound as e:
            printcolor(f"Error: {e.message}", RED)
            return
        
        followings2 = self._get_user_followings(target2_id)

        table = prettytable.PrettyTable()
        table.field_names = ["pk", "username", "full_name"]

        if self.json:
            data = []

        subset = [user for user in followings if user in followings2]
        for user in subset:
            table.add_row([user["pk"], user["username"], user["full_name"]])
            
            if self.json:
                data.append(user)

        print(table.get_string())
        printcolor(f"Found {len(subset)} common followings", GREEN)

        self._save_to_files(data, table, f"followings-subset_{target2}", f"and {target2} followings subset")
        
    def hashtags(self) -> None:
        captions = self._get_captions()

        table = prettytable.PrettyTable()
        table.field_names = ["id", "taken_at", "hashtag_id", "name", "media_count", "profile_pic_url"]

        if self.json:
            data = {}

        hashtag_posts = []
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._get_hashtag_data, caption) for caption in captions]
            for idx, future in enumerate(futures):
                remaining_time = calculate_remaining_time(start_time, idx, len(captions))
                printcolor(f"Checking post {idx + 1} of {len(captions)}. Remaining time: {remaining_time}", BLUE, end="\033[K\r")
                try:
                    result = future.result()
                except Exception as e:
                    printcolor(f"{YELLOW}{repr(future)}{RESET} generated an exception: {e}", RED)
                else:
                    if result:
                        hashtag_posts.append(result)
        print()

        post_count = 0
        hashtag_count = 0
        for post in hashtag_posts:
            for hashtag in post[1]:
                table.add_row([post[0], *hashtag.values()[:-1]])
                hashtag_count += 1
            if self.json:
                data[post[0]] = post[1]
            post_count += 1

        if hashtag_count == 0:
            printcolor("No hashtags found", RED)
            return

        print(table.get_string())
        printcolor(f"Found {post_count} post with hashtags. Total hashtags: {hashtag_count}", GREEN)

        self._save_to_files(data, table, "hashtags")
        
    def highlights(self) -> None:
        highlight_folders = [highlight_folder.dict() for highlight_folder in self.client.user_highlights_v1(self.target_id)]

        if not (highlight_idxs := self.parse_extra_input()) and self.interactive:
            for idx, folder in enumerate(highlight_folders):
                printcolor(f"{idx}={folder['title']}  ", BLUE, end="")
            highlight_idxs = inputcolor("\nEnter highlight folder numbers to download (comma separated): ", CYAN)

        try:
            download_folders = [highlight_folders[int(idx)] for idx in highlight_idxs.replace(" ", "").split(",")] if highlight_idxs else highlight_folders
        except ValueError:
            printcolor(f"Invalid highlight folder number: {idx}", RED)
            return

        count = self._download_highlights(download_folders)

        if count == 0:
            printcolor("No highlights found", RED)

    def info(self) -> None:
        user_info = self._get_user_info_v1()

        for k, v in user_info.items():
            if v:
                printcolor(f"{k}: {WHITE}{v}", BLUE)

        if self.json:
            filename = f"{user_info['username']}_info"
            self._write_json(user_info, filename)
            printcolor(f"Successfully saved {self.target_name} info to {filename}.json", GREEN)

    def info_list(self) -> None:
        if not self.json:
            printcolor("JSON output is required", RED)
            return

        printcolor("WARNING! Currently instagram throws 401 error for the user info request through the graphql api.\n"
            "For now these requests are made through the mobile api which has a much lower rate limit.\n"
            "Please use this function lightly to avoid being blocked by instagram.", YELLOW)

        if not (filename := self.parse_extra_input()) and self.interactive:
            filename = inputcolor("Filename (relative to the output dir): ", CYAN)
        
        valid_names = ["_comments.json", "_followers.json", "_followers-subset.json", "_followings.json", "_followings-subset.json",
            "_likers.json", "_tagged.json", "_tagged-target.json", "_tagged-with.json"]
        if not (os.path.isfile(f"{self.output}/{filename}") and re.findall("|".join(valid_names), filename)):
            printcolor(f"No valid file exists with the name: {filename}", RED)
            return

        with open(f"{self.output}/{filename}") as f:
            data = json.load(f)

        if (user_dicts := self.parse_info_list(data)) is None:
            printcolor("Invalid file structure", RED)
            return

        if not (input_min_idx := self.parse_extra_input()) and self.interactive:
            input_min_idx = inputcolor("Starting index (inclusive): ", CYAN)
        try:
            min_idx = int(input_min_idx) if input_min_idx else 0
        except ValueError:
            printcolor("Invalid starting index", RED)
            return
            
        if not (input_max_idx := self.parse_extra_input()) and self.interactive:
            input_max_idx = inputcolor("Ending index (non-inclusive): ", CYAN)
        try:
            max_idx = int(input_max_idx) if input_max_idx else len(user_dicts)
        except ValueError:
            printcolor("Invalid ending index", RED)
            return

        users = self._get_user_info_gql_threaded(user_dicts[min_idx:max_idx])

        printcolor(f"Collected {len(users)} user info", GREEN)
        
        output_filename = f"{filename.replace('.json', '')}_{min_idx}_{max_idx}_info"
        self._write_json(users, output_filename)
        printcolor(f"Successfully saved {self.target_name} followers info to {output_filename}.json", GREEN)

    def likes(self) -> None:
        posts = self._get_user_medias()
        media_types = {
            1: "photo",
            2: "video",
            8: "album"
        }

        table = prettytable.PrettyTable()
        table.field_names = ["id", "taken_at", "media_type", "like_count", "has_liked", "sum"]

        if self.json:
            data = {}

        rolling_sum = 0
        for post in posts:
            rolling_sum += post["like_count"]
            table.add_row([
                post["id"],
                int(post["taken_at"].timestamp()),
                media_types[post["media_type"]],
                post["like_count"],
                post["has_liked"],
                rolling_sum
            ])

            if self.json:
                data[post["id"]] = {
                    "taken_at": int(post["taken_at"].timestamp()),
                    "media_type": media_types[post["media_type"]],
                    "like_count": post["like_count"],
                    "has_liked": post["has_liked"],
                    "sum": rolling_sum
                }

        print(table.get_string())
        printcolor(f"Found {len(posts)} posts, with total likes: {rolling_sum}", GREEN)

        self._save_to_files(data, table, "likes")

    def likers(self) -> None:
        posts = self._get_user_medias()

        table = prettytable.PrettyTable()
        table.field_names = ["id", "pk", "username", "full_name"]

        if self.json:
            data = {}

        likers = self._get_media_likers_threaded(posts)

        post_count = 0
        for post in likers:
            for user in post[1]:
                table.add_row([post[0], user["pk"], user["username"], user["full_name"]])
            if self.json:
                data[post[0]] = post[1]
            post_count += 1

        if post_count == 0:
            printcolor("No posts found", RED)
            return

        print(table.get_string())
        printcolor(f"Found {post_count} posts.", GREEN)

        self._save_to_files(data, table, "likers")
        
    def locations(self) -> None:
        posts = self._get_user_medias()

        table = prettytable.PrettyTable()
        table.field_names = ["id", "taken_at", "loc_pk", "name", "address", "lat", "lng"]
        table.max_width["address"] = 50

        if self.json:
            data = {}

        location_posts = []
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._get_location_data, post) for post in posts]
            for idx, future in enumerate(futures):
                remaining_time = calculate_remaining_time(start_time, idx, len(posts))
                printcolor(f"Checking post {idx + 1} of {len(posts)}. Remaining time: {remaining_time}", BLUE, end="\033[K\r")
                try:
                    result = future.result()
                except Exception as e:
                    printcolor(f"{YELLOW}{repr(future)}{RESET} generated an exception: {e}", RED)
                else:
                    if result:
                        location_posts.append(result)
        print()

        count = 0
        for post in location_posts:
            table.add_row([post[0], *post[1].values()])
            if self.json:
                data[post[0]] = post[1]
            count += 1

        if count == 0:
            printcolor("No locations found", RED)
            return

        print(table.get_string())
        printcolor(f"Found {count} locations", GREEN)

        self._save_to_files(data, table, "locations")
        
    def posts(self) -> None:
        posts = self._get_user_medias()
        
        if not (user_input := self.parse_extra_input()) and self.interactive:
            user_input = inputcolor("Enter number of posts to download: ", CYAN)
        
        try:
            limit = int(user_input) if user_input else len(posts)
        except ValueError:
            printcolor("Invalid number", RED)
            return

        count = self._download_media_threaded(posts[:limit])
        print()
        
        if count == 0:
            printcolor("No posts found", RED)

    def posts_data(self) -> None:
        if not self.json:
            printcolor("JSON output is required", RED)
            return
        
        posts = self._get_user_medias()

        name = f"{self.target_name}_posts-data"
        self._write_json(posts, name)
        printcolor(f"Successfully saved {self.target_name} posts data to {name}.json", GREEN)

    def posts_tagged(self) -> None:
        posts = self._get_usertag_medias()

        if not (user_input := self.parse_extra_input()) and self.interactive:
            user_input = inputcolor("Enter number of posts to download: ", CYAN)
        
        try:
            limit = int(user_input) if user_input else len(posts)
        except ValueError:
            printcolor("Invalid number", RED)
            return

        count = self._download_media_threaded(posts[:limit])
        print()
        
        if count == 0:
            printcolor("No posts found", RED)

    def posts_tagged_data(self) -> None:
        if not self.json:
            printcolor("JSON output is required", RED)
            return
        
        posts = self._get_usertag_medias()

        name = f"{self.target_name}_posts-tagged-data"
        self._write_json(posts, name)
        printcolor(f"Successfully saved {self.target_name} posts tagged data to {name}.json", GREEN)

    def profile_pic(self) -> None:
        user_info = self._get_user_info_v1()
        name = f"{self.target_name}_profile-pic.jpg"
        self._download_media({
            "url": user_info["profile_pic_url_hd"],
            "path": f"{self.output}/{name}"
        })
        printcolor(f"Successfully saved {self.target_name} profile pic to {name}", GREEN)

    def stories(self) -> None:
        stories = self._get_user_stories()
        count = self._download_media_threaded(stories)
        print()
        
        if count == 0:
            printcolor("No stories found", RED)
    
    def tagged(self) -> None:
        posts = self._get_user_medias()

        table = prettytable.PrettyTable()
        table.field_names = ["id", "taken_at", "user_pk", "username", "full_name"]

        if self.json:
            data = {}

        count = 0
        for post in posts:
            if not (tags := post["usertags"]):
                continue

            for tag in tags:
                table.add_row([post["id"], post["taken_at"], tag["user"]["pk"], tag["user"]["username"], tag["user"]["full_name"]])
                count += 1

            if self.json:
                data[post["id"]] = {"taken_at": post["taken_at"], "usertags": tags}

        print(table.get_string())
        printcolor(f"Found {count} usertags", GREEN)
        
        self._save_to_files(data, table, "tagged", "tagged data")

    def tagged_target(self) -> None:
        posts = self._get_usertag_medias()

        table = prettytable.PrettyTable()
        table.field_names = ["id", "taken_at", "user_pk", "username", "full_name"]

        if self.json:
            data = {}

        count = 0
        for post in posts:
            table.add_row([post["id"], post["taken_at"], post["user"]["pk"], post["user"]["username"], post["user"]["full_name"]])
            if self.json:
                data[post["id"]] = {"taken_at": post["taken_at"], "user": post["user"]}
            count += 1

        print(table.get_string())
        printcolor(f"Found {count} usertags", GREEN)

        self._save_to_files(data, table, "tagged-target", "tagged target data")

    def tagged_with(self) -> None:
        posts = self._get_usertag_medias()

        table = prettytable.PrettyTable()
        table.field_names = ["id", "taken_at", "user_pk", "username", "full_name"]

        if self.json:
            data = {}

        count = 0
        for post in posts:
            if not (tags := post["usertags"]):
                continue

            for tag in tags:
                if tag["user"]["pk"] != self.target_id:    
                    table.add_row([post["id"], post["taken_at"], tag["user"]["pk"], tag["user"]["username"], tag["user"]["full_name"]])
                    count += 1

            if self.json:
                data[post["id"]] = {"taken_at": post["taken_at"], "usertags": [tag for tag in tags if tag["user"]["pk"] != self.target_id]}

        print(table.get_string())
        printcolor(f"Found {count} usertags", GREEN)

        self._save_to_files(data, table, "tagged-with", "tagged with data")

    def target(self) -> None:
        if not (new_target := self.parse_extra_input()) and self.interactive:
            new_target = inputcolor("Enter new target username: ", CYAN)
        
        if self.target_name == new_target or not new_target:
            printcolor(f"Target already set to {MAGENTA}{self.target_name}", GREEN)
            return
        
        self.target_name = new_target
        self._print_target()

    def viewcount(self) -> None:
        posts = self._get_user_medias()

        table = prettytable.PrettyTable()
        table.field_names = ["id", "taken_at", "view_count", "sum"]

        if self.json:
            data = {}

        rolling_sum = 0
        count = 0
        for post in posts:
            if post["media_type"] == 2:
                rolling_sum += post["view_count"]
                table.add_row([post["id"], int(post["taken_at"].timestamp()), post["view_count"], rolling_sum])

                if self.json:
                    data[post["id"]] = {
                        "taken_at": int(post["taken_at"].timestamp()),
                        "view_count": post["view_count"],
                        "sum": rolling_sum
                    }

                count += 1

        print(table.get_string())
        printcolor(f"Found {count} videos, with total viewcount: {rolling_sum}", GREEN)

        self._save_to_files(data, table, "viewcount")


    def _save_to_files(self, data: dict[str, Any], table: prettytable.PrettyTable, filename_suffix: str, text: str = None):
        filename = f"{self.target_name}_{filename_suffix}"
        if self.json:
            self._write_json(data, filename)
            printcolor(f"Successfully saved {self.target_name} {text or filename_suffix} to {filename}.json", GREEN)

        if self.txt:
            table.set_style(self.table_style)
            self._write_txt(table.get_string(), filename)
            printcolor(f"Successfully saved {self.target_name} {text or filename_suffix} to {filename}.txt", GREEN)
        
    ### LOGIN ###
    def _login(self) -> None:
        if not self.username or not self.password:
            self.username = inputcolor("Enter username: ", CYAN)
            self.password = inputcolor("Enter password: ", CYAN)
            self._set_credentials()

        if os.path.isfile(self.settings_path): 
            self.client.load_settings(self.settings_path)

        try:
            self.client.login(self.username, self.password, verification_code=self.verification_code or "")
            self.client.dump_settings(self.settings_path)

        except (TwoFactorRequired, UnknownError): # Throws UnknownError when the code is wrong
            self.verification_code = inputcolor("Enter 2FA code: ", CYAN)
            self._login()

        except ClientError as e:
            printcolor(f"Error: {e.message}", RED)
            printcolor(f"Code: {e.code}", RED)
            printcolor(f"Response: {e.response}", RED)
            sys.exit(1)
    
    def _get_credentials(self) -> dict[str, str]:
        try:
            with open(self.credentials_path) as f:
                return json.load(f)
        except FileNotFoundError:
            return {"username": "", "password": ""}

    def _set_credentials(self) -> None:
        with open(self.credentials_path, "w") as f:
            json.dump({"username": self.username, "password": self.password}, f, indent=4, ensure_ascii=False, default=str)

    ### HELPERS ###    
    def _download_highlights(self, download_folders: list) -> int:
        medias = []
        duplicate_names = [name for name in download_folders if download_folders.count(name) > 1]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.client.highlight_info_v1, folder["pk"]) for folder in download_folders]
            for future in futures:
                try:
                    result = future.result().dict()
                except Exception as e:
                    printcolor(f"{YELLOW}{repr(future)}{RESET} generated an exception: {e}", RED)
                else:
                    title = f"{result['title'] + ('_' + result['pk'] if result['title'] in duplicate_names else '')}"
                    path = f"{self.output}/{title}"
                    os.makedirs(path, exist_ok=True)
                    self._download_media({
                        "url": result["cover_media"]["cropped_image_version"]["url"],
                        "path": f"{path}/{self.target_name}_{title}_cover.jpg"
                    })
                    medias.extend({"item": item, "path": f"{self.output}/{title}"} for item in result["items"])

        return self._download_media_threaded(medias)
    
    def _download_media(self, data: dict[str, Any]) -> None:
        media = data.get("item", data)
        path = data.get("path", self.output)

        if "media_type" in media:
            if (username := media["user"]["username"]) is None or username == self.target_name:
                name_prefix = self.target_name
            else:
                name_prefix = f"{self.target_name}_tagged-by_{username}"
            
            filename = f"{name_prefix}_{media['pk']}_{int(media['taken_at'].timestamp())}"
            match media["media_type"]:
                case 1:
                    url = media["thumbnail_url"]
                    urllib.request.urlretrieve(url, f"{path}/{filename}.jpg")
                case 2:
                    url = media["video_url"]
                    urllib.request.urlretrieve(url, f"{path}/{filename}.mp4")
        else:
            urllib.request.urlretrieve(media["url"], path)
    
    def _download_media_threaded(self, medias: list[dict]) -> int:
        for idx, data in enumerate(medias):
            if data.get("media_type", None) == 8:
                for item in reversed(data["resources"]):
                    medias.insert(idx, {"taken_at": data["taken_at"], **item})
        
        count = 0
        total = len(medias)
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._download_media, media) for media in medias]
            for future in concurrent.futures.as_completed(futures):
                try:
                    _ = future.result()
                except Exception as e:
                    printcolor(f"{YELLOW}{repr(future)}{RESET} generated an exception: {e}", RED)
                else:
                    count += 1
                    remaining_time = calculate_remaining_time(start_time, count, total)
                    printcolor(f"Downloaded {count} {'files' if count > 1 else 'file'}. {BLUE}Remaining time: {remaining_time}", GREEN, end="\033[K\r")
        print()

        return count

    def _get_captions(self) -> list[dict[str, str | int]]:
        posts = self._get_user_medias()
        return [{
            "id": post["id"],
            "taken_at": int(post["taken_at"].timestamp()),
            "caption": post["caption_text"]
        } for post in posts]

    def _get_comments(self, id: str) -> tuple[str, list[dict[str, Any]]]:
        comments = self.client.media_comments(id)
        return (id, [comment.dict() for comment in comments])

    def _get_comments_threaded(self, posts: list) -> list[tuple[str, list[dict[str, Any]]]]:
        comments = []
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(self._get_comments, post["id"]) for post in posts]
            for idx, future in enumerate(futures):
                remaining_time = calculate_remaining_time(start_time, idx, len(posts))
                printcolor(f"Checking post {idx + 1} of {len(posts)}. Remaining time: {remaining_time}", BLUE, end="\033[K\r")
                try:
                    result = future.result()
                except Exception as e:
                    printcolor(f"{YELLOW}{repr(future)}{RESET} generated an exception: {e}", RED)
                else:
                    if result[1]:
                        comments.append(result)
        print()

        return comments

    def _get_hashtag_data(self, caption: str) -> tuple[str, list[dict[str, str | int]]]:
        if hashtags := re.findall("#\w*[a-zA-Z]+\w*", caption["caption"]):
            return (
                caption[0],
                [{
                    "taken_at": caption[1]["taken_at"],
                    **self.client.hashtag_info_gql(hashtag[1:]).dict()
                } for hashtag in hashtags]
            )
        return None

    def _get_location_data(self, post: list) -> tuple[str, dict[str, str | int]]:
        if post["location"]:
            location_data = geopy.geocoders.Nominatim(user_agent="intelgram").reverse(f"{post['location']['lat']}, {post['location']['lng']}")
            return (
                post["id"],
                {
                    "taken_at": int(post["taken_at"].timestamp()),
                    "loc_pk": post["location"]["pk"],
                    "name": post["location"]["name"],
                    "address": location_data.address,
                    "lat": location_data.latitude,
                    "lng": location_data.longitude
                }
            )
        return None

    def _get_media_likers(self, id: str) -> list[tuple[str, list[dict[str, Any]]]]:
        likers = self.client.media_likers(id)
        return (id, [liker.dict() for liker in likers])

    def _get_media_likers_threaded(self, posts: list) -> list[tuple[str, list[dict[str, Any]]]]:
        likers = []
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(self._get_media_likers, post["id"]) for post in posts]
            for idx, future in enumerate(futures):
                remaining_time = calculate_remaining_time(start_time, idx, len(posts))
                printcolor(f"Checking post {idx + 1} of {len(posts)}. Remaining time: {remaining_time}", BLUE, end="\033[K\r")
                try:
                    result = future.result()
                except Exception as e:
                    printcolor(f"{YELLOW}{repr(future)}{RESET} generated an exception: {e}", RED)
                else:
                    if result[1]:
                        likers.append(result)
        print()

        return likers

    def _get_user_followers(self, pk: str = None) -> list[dict[str, Any]]:
        return [user.dict() for user in self.client.user_followers_v1(pk or self.target_id)]
        
    def _get_user_followings(self, pk: str = None) -> list[dict[str, Any]]:
        return [user.dict() for user in self.client.user_following_v1(pk or self.target_id)]

    def _get_user_info_v1(self, pk: str = None) -> dict[str, Any]:
        return self.client.user_info_v1(pk or self.target_id).dict()

    def _get_user_info_gql(self, pk: str = None) -> dict[str, Any]:
        # Currently (2022 october) user_info_gql throws 401 unauthorized url error
        # return self.client.user_info_gql(pk or self.target_id).dict()
        return self.client.user_info_v1(pk or self.target_id).dict()

    def _get_user_info_gql_threaded(self, users: list) -> list[dict[str, Any]]:
        data = []
        max_workers = 4 if len(users) < 100 else 2 if len(users) < 200 else 1
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._get_user_info_gql, pk) for pk in users]
            for idx, future in enumerate(futures):
                remaining_time = calculate_remaining_time(start_time, idx, len(users))
                printcolor(f"Getting user {idx + 1} of {len(users)} users. Remaining time: {remaining_time}", BLUE, end="\033[K\r")
                try:
                    result = future.result()
                except Exception as e:
                    printcolor(f"{YELLOW}{repr(future)}{RESET} generated an exception: {e}", RED)
                else:
                    data.append(result)
        print()
        
        return data

    def _get_user_medias(self) -> list[dict[str, Any]]:
        return [media.dict() for media in self.client.user_medias_v1(self.target_id)]

    def _get_user_stories(self) -> list[dict[str, Any]] | list:
        try:
            return [story.dict() for story in self.client.user_stories_v1(self.target_id)]
        except IndexError:
            return []

    def _get_usertag_medias(self) -> list[dict[str, Any]]:
        return [usertag.dict() for usertag in self.client.usertag_medias_v1(self.target_id)]

    def parse_extra_input(self) -> str:
        return self.extra_input.pop(0) if self.extra_input else ""

    def parse_info_list(self, data: list[Any] | dict[str, Any]) -> list[dict[str, Any]] | None:
        users = []
        if isinstance(data, list):
            # followers, followings, followers-subset, followings-subset
            users.append((user["pk"] for user in data))
        elif isinstance(data, dict):
            # commenters, likers, tagged, tagged-target, tagged-with
            for v in data.values():
                if isinstance(v, list):
                    # commenters, likers
                    users.append((item["user"]["pk"] if "user" in item else item["pk"] for item in v))
                elif isinstance(v, dict):
                    # tagged, tagged-target, tagged-with
                    if "usertags" in v:
                        # tagged, tagged-with
                        users.append((item["user"]["pk"] for item in v["usertags"]))
                    else:
                        # tagged-target
                        users.append(v["user"]["pk"])
                else:
                    return None
        else:
            return None
            
        return list(dict.fromkeys(users))

    def _print_target(self) -> None:
        printcolor(f"Searching for {MAGENTA}{self.target_name}", BLUE, end="\033[K\r")
        
        try:
            self.target_id = self.client.user_id_from_username(self.target_name)
        except UserNotFound as e:
            printcolor(f"Error: {e.message}", RED)
            sys.exit(1)
        
        friendship = self.client.user_friendship_v1(self.target_id).dict()
        is_private = ""
        if friendship["is_private"]:
            is_private = f"{RED}(PRIVATE){RESET}"
        else:
            is_private = f"{GREEN}(PUBLIC){RESET}"
        
        status = ""
        if friendship["following"] and friendship["followed_by"]:
            status = f"{GREEN}(FOLLOWING & FOLLOWED BY){RESET}"
        elif friendship["following"]:
            status = f"{YELLOW}(FOLLOWING){RESET}"
        elif friendship["followed_by"]:
            status = f"{YELLOW}(FOLLOWED BY){RESET}"
        else:
            status = f"{RED}(NOT FOLLOWING & NOT FOLLOWED BY){RESET}"
        
        printcolor(f"Target: {MAGENTA}{self.target_name} {BLUE}[{self.target_id}] {is_private} {status}", GREEN)
    
    def _write_json(self, data: dict | list, name: str) -> None:
        with open(f"{self.output}/{name}.json", "w") as f:
            json.dump(data, f, indent=4, ensure_ascii=False, default=str)

    def _write_txt(self, data: dict | list, name: str) -> None:
        with open(f"{self.output}/{name}.txt", "w") as f:
            f.write(data)
