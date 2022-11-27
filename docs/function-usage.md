This is for explaining which api endpoint (gql vs v1) is used and why.
Version: `instagrapi==1.16.29`

### hashtag_info_gql vs hashtag_info_v1
- gql has profile pic url, v1 and default not.
- Use: gql

### user_followers_gql vs user_followers_v1
- gql has random order, v1 lists first the accounts that you follow. The default function only returns user ids.
- Use: v1

### user_following_gql vs user_following_v1
- gql only returns an empty array. The default function only returns user ids.
- Use: v1

### user_highlights and highlight_info
- Internally both just call v1. No gql exists.

### user_info_gql vs user_info_v1
- v1 has: account_type, interop_messaging_user_fbid
- For bulk usages use gql

### user_medias_gql vs user_medias_v1
- v1 returns user dicts with complete data, has accurate has_liked data, and if the post has location it returns lat lng values.
- Use: v1

### user_stories_gql vs user_stories_v1
- v1 has user dicts with full_name, is_private data, mentions have complete data
- Use: v1

### usertag_gql vs usertag_v1
- v1 has location, better user dict, and usertags on post, not just that the target is tagged on it
- Use: v1
