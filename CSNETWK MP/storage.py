# storage.py
import threading

peers = {}      # {user_id: {"display_name": str, "status": str}}
posts = []      # [{"user_id": str, "content": str, "timestamp": int}]
dms = []        # [{"from": str, "to": str, "content": str}]
followers = set()  # {"alice@192.168.1.11", ...}
groups = {}     # {group_id: {"name": str, "members": [user_ids]}}
likes = []      # [{"from": str, "to": str, "post_timestamp": int, "action": "LIKE"}]

storage_lock = threading.Lock()  # Lock for thread-safe access
incoming_files = {} # {fileid: {"from": str, "filename": str, "filesize": int, "filetype": str, "description": str}}