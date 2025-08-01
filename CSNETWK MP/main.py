import os
import threading
import time
import random
import config
import base64
from config import USER_ID, DISPLAY_NAME, STATUS, TTL_DEFAULT
from parser import build_message, parse_message
from network import send_broadcast, listen
from storage import peers, posts, dms, followers, groups, likes, storage_lock, incoming_files
from logger import print_non_verbose, log

def handle_message(raw_msg: str, addr):
    try:
        msg = parse_message(raw_msg)
        msg_type = msg.get("TYPE")
        sender_id = msg.get("USER_ID") or msg.get("FROM")

        if sender_id == USER_ID:
           return  # Ignore self
        
        # PING
        if msg_type == "PING":
            log(f"PING received from {sender_id}")
            return

        # PROFILE
        if msg_type == "PROFILE":
            display_name = msg.get("DISPLAY_NAME", sender_id)
            status = msg.get("STATUS", "")
            if sender_id not in peers or peers[sender_id]["status"] != status:
                peers[sender_id] = {"display_name": display_name, "status": status}
                print_non_verbose(f"[PROFILE] {display_name} - {status}")

        # POST
        elif msg_type == "POST":
            posts.append({"user_id": sender_id, "content": msg.get("CONTENT", ""), "timestamp": msg.get("TTL")})
            display_name = peers.get(sender_id, {}).get("display_name", sender_id)
            print_non_verbose(f"[POST] {display_name}: {msg.get('CONTENT')}")

        # DM
        elif msg_type == "DM":
            dms.append({"from": msg.get("FROM"), "to": msg.get("TO"), "content": msg.get("CONTENT")})
            sender = peers.get(msg.get("FROM"), {}).get("display_name", msg.get("FROM"))
            print_non_verbose(f"[DM] {sender}: {msg.get('CONTENT')}")

        # FOLLOW
        elif msg_type == "FOLLOW":
            followers.add(sender_id)
            print_non_verbose(f"User {sender_id} has followed you")

        # UNFOLLOW
        elif msg_type == "UNFOLLOW":
            if sender_id in followers:
                followers.remove(sender_id)
            print_non_verbose(f"User {sender_id} has unfollowed you")

        # LIKE
        elif msg_type == "LIKE":
            likes.append({"from": msg.get("FROM"), "to": msg.get("TO"), "post_timestamp": msg.get("POST_TIMESTAMP"), "action": msg.get("ACTION")})
            liker = peers.get(msg.get("FROM"), {}).get("display_name", msg.get("FROM"))

            post_content = None
            for p in posts:
                if str(p["timestamp"]) == str(msg.get("POST_TIMESTAMP")) and p["user_id"] == msg.get("TO"):
                    post_content = p["content"]
                    break
            
            if msg.get("ACTION") == "LIKE":
                if post_content:
                    print_non_verbose(f"{liker} likes your post [{post_content}]")
                else:
                    print_non_verbose(f"{liker} likes your post")
            elif msg.get("ACTION") == "UNLIKE":
                if post_content:
                    print_non_verbose(f"{liker} unlikes your post [{post_content}]")
                else:
                    print_non_verbose(f"{liker} unlikes your post")


        elif msg_type == "GROUP_CREATE":
            try:
                members = [m.strip() for m in msg.get("MEMBERS", "").split(",") if m.strip()]
                creator = msg.get("FROM")
                
                
                if creator not in members:
                    members.append(creator)
                    
                
                with storage_lock:
                    groups[msg.get("GROUP_ID")] = {
                        "name": msg.get("GROUP_NAME"),
                        "creator": creator,
                        "members": members
                    }
                    
                print(f"DEBUG: Stored group {msg.get('GROUP_ID')} with members {members}")
                print_non_verbose(f"Group '{msg.get('GROUP_NAME')}' created by {creator} with members: {', '.join(members)}")
                print_non_verbose(f"You've been added to {msg.get('GROUP_NAME')}")
            except Exception as e:
                log(f"Group creation failed: {e}")
    
        elif msg_type == "GROUP_UPDATE":
            group_id = msg.get("GROUP_ID")
            if group_id in groups:
                # Update membership
                add_members = [m for m in msg.get("ADD", "").split(",") if m] if msg.get("ADD") else []
                remove_members = [m for m in msg.get("REMOVE", "").split(",") if m] if msg.get("REMOVE") else []
                
                
                groups[group_id]["members"].extend(add_members)
                
                
                for r in remove_members:
                    if r in groups[group_id]["members"]:
                        groups[group_id]["members"].remove(r)
                
               
                group_name = groups[group_id]["name"]
                print_non_verbose(f"The group '{group_name}' member list was updated.")
            else:
                log(f"GROUP_UPDATE: Unknown group {group_id}")

        # GROUP_MESSAGE
        elif msg_type == "GROUP_MESSAGE":
            group_id = msg.get("GROUP_ID")
            print(f"DEBUG: Checking group {group_id} in {groups.keys()}")
            print(f"DEBUG: Our USER_ID is {USER_ID}")
            
            if group_id in groups and USER_ID in groups[group_id]["members"]:
                sender = peers.get(msg.get("FROM"), {}).get("display_name", msg.get("FROM"))
                group_name = groups[group_id]["name"]
                print_non_verbose(f"[GROUP:{group_name}] {sender}: {msg.get('CONTENT')}")
            else:
                log(f"GROUP_MESSAGE: Not a member of {group_id}")

        
        elif msg_type == "TICTACTOE_INVITE":
            from tictactoe import handle_tictactoe_invite
            handle_tictactoe_invite(msg, sender_id)
            
        elif msg_type == "TICTACTOE_MOVE":
            from tictactoe import handle_tictactoe_move
            handle_tictactoe_move(msg, sender_id)
            
        elif msg_type == "TICTACTOE_RESULT":
            from tictactoe import handle_tictactoe_result
            handle_tictactoe_result(msg, sender_id)
            
        elif msg_type == "FILE_OFFER":
            if msg.get("TO") == USER_ID:
                fileid = msg.get("FILEID")
                with storage_lock:
                    # Skip if already processing
                    if fileid in incoming_files:
                        return
                    
                    
                    incoming_files[fileid] = {
                        "from": msg.get("FROM"),
                        "filename": msg.get("FILENAME"),
                        "filesize": msg.get("FILESIZE"),
                        "filetype": msg.get("FILETYPE"),
                        "description": msg.get("DESCRIPTION", ""),
                        "timestamp": time.time(),
                        "chunks": {},
                        "received_chunks": set(),
                        "total_chunks": None,
                        "accepted": False  
                    }
                
                display_name = peers.get(msg.get("FROM"), {}).get("display_name", msg.get("FROM"))
                print_non_verbose(f"User {display_name} is sending you a file. Do you accept? (Type 'accept {fileid}')")
                
        # FILE_CHUNK
        elif msg_type == "FILE_CHUNK":
            fileid = msg.get("FILEID")
            print(f"DEBUG: Received chunk for fileid: {fileid}")
            with storage_lock:
                
                if fileid not in incoming_files:
                    log(f"Ignoring chunk for unaccepted file: {fileid}")
                    return
                
                file_rec = incoming_files[fileid]
                
                
                if not file_rec.get("accepted", False):
                    log(f"Ignoring chunk for unaccepted file: {fileid}")
                    return
                
                idx = int(msg.get("CHUNK_INDEX"))
                total = int(msg.get("TOTAL_CHUNKS"))
                
                # Initialize if first chunk
                if file_rec["total_chunks"] is None:
                    file_rec["total_chunks"] = total
                elif file_rec["total_chunks"] != total:
                    log("Total chunks mismatch")
                    return
                
              
                file_rec["chunks"][idx] = msg.get("DATA")
                file_rec["received_chunks"].add(idx)
                
                log(f"Received chunk {idx+1}/{total} for {file_rec['filename']}")
                
               
                if len(file_rec["received_chunks"]) == total:
                    threading.Thread(target=reassemble_file, args=(fileid,)).start()

        # FILE_RECEIVED
        elif msg_type == "FILE_RECEIVED":
            
            log(f"File {msg.get('FILEID')} received by {msg.get('FROM')}")

    except Exception as e:
        log(f"Error parsing message: {e}")

def periodic_broadcast():
    """Sends PING and PROFILE every 10 seconds."""
    while True:
        ping_msg = build_message({"TYPE": "PING", "USER_ID": USER_ID})
        send_broadcast(ping_msg)

        profile_msg = build_message({
            "TYPE": "PROFILE",
            "USER_ID": USER_ID,
            "DISPLAY_NAME": DISPLAY_NAME,
            "STATUS": STATUS
        })

        
        send_broadcast(profile_msg)
        time.sleep(10)  

def send_post(content: str):
    message_id = hex(random.getrandbits(64))[2:]
    timestamp = int(time.time())
    token = f"{USER_ID}|{timestamp + TTL_DEFAULT}|broadcast"
    post_msg = build_message({
        "TYPE": "POST",
        "USER_ID": USER_ID,
        "CONTENT": content,
        "TTL": TTL_DEFAULT,
        "MESSAGE_ID": message_id,
        "TOKEN": token
    })
    send_broadcast(post_msg)
    log(f"POST SENT: {content}")

def send_dm(target_user: str, content: str):
    timestamp = int(time.time())
    message_id = hex(random.getrandbits(64))[2:]
    token = f"{USER_ID}|{timestamp + TTL_DEFAULT}|chat"
    dm_msg = build_message({
        "TYPE": "DM",
        "FROM": USER_ID,
        "TO": target_user,
        "CONTENT": content,
        "TIMESTAMP": timestamp,
        "MESSAGE_ID": message_id,
        "TOKEN": token
    })
    send_broadcast(dm_msg)
    log(f"DM SENT to {target_user}: {content}")

def send_follow(target_user: str):
    timestamp = int(time.time())
    message_id = hex(random.getrandbits(64))[2:]
    token = f"{USER_ID}|{timestamp + TTL_DEFAULT}|follow"

    follow_msg = build_message({
        "TYPE": "FOLLOW",
        "USER_ID": USER_ID,
        "TARGET_USER_ID": target_user,
        "TIMESTAMP": timestamp,
        "MESSAGE_ID": message_id,
        "TOKEN": token
    })
    send_broadcast(follow_msg)
    log(f"FOLLOW SENT to {target_user}")

def send_unfollow(target_user: str):
    timestamp = int(time.time())
    message_id = hex(random.getrandbits(64))[2:]
    token = f"{USER_ID}|{timestamp + TTL_DEFAULT}|follow"

    unfollow_msg = build_message({
        "TYPE": "UNFOLLOW",
        "USER_ID": USER_ID,
        "TARGET_USER_ID": target_user,
        "TIMESTAMP": timestamp,
        "MESSAGE_ID": message_id,
        "TOKEN": token
    })
    send_broadcast(unfollow_msg)
    log(f"UNFOLLOW SENT to {target_user}")

def send_like(target_user: str, post_timestamp: int, action: str = "LIKE"):
    """Send a LIKE or UNLIKE message for a specific post."""
    timestamp = int(time.time())
    message_id = hex(random.getrandbits(64))[2:]
    token = f"{USER_ID}|{timestamp + TTL_DEFAULT}|broadcast"

    like_msg = build_message({
        "TYPE": "LIKE",
        "FROM": USER_ID,
        "TO": target_user,
        "POST_TIMESTAMP": post_timestamp,
        "ACTION": action,
        "TIMESTAMP": timestamp,
        "MESSAGE_ID": message_id,
        "TOKEN": token
    })
    send_broadcast(like_msg)
    
    
    likes.append({
        "from": USER_ID,
        "to": target_user,
        "post_timestamp": post_timestamp,
        "action": action,
        "timestamp": timestamp
    })
    
    log(f"{action} SENT to {target_user} for post at {post_timestamp}")

def reassemble_file(fileid: str):
    with storage_lock:
        if fileid not in incoming_files:
            return
        file_rec = incoming_files.pop(fileid)

    try:
      
        data = b""
        for i in range(file_rec["total_chunks"]):
            chunk = file_rec["chunks"].get(i)
            if not chunk:
                raise ValueError(f"Missing chunk {i}")
            data += base64.b64decode(chunk)
        
      
        filename = file_rec["filename"]
        os.makedirs("received_files", exist_ok=True)
        path = os.path.join("received_files", filename)
        
       
        counter = 1
        base_name, ext = os.path.splitext(filename)
        while os.path.exists(path):
            path = os.path.join("received_files", f"{base_name}_{counter}{ext}")
            counter += 1
            
        with open(path, "wb") as f:
            f.write(data)
            
        print_non_verbose(f"File transfer of {filename} is complete")
        
        
        timestamp = int(time.time())
        msg_id = hex(random.getrandbits(64))[2:]
        token = f"{USER_ID}|{timestamp+TTL_DEFAULT}|file"
        received_msg = build_message({
            "TYPE": "FILE_RECEIVED",
            "FROM": USER_ID,
            "TO": file_rec["from"],
            "FILEID": fileid,
            "STATUS": "COMPLETE",
            "TIMESTAMP": timestamp,
            "MESSAGE_ID": msg_id,
            "TOKEN": token
        })
        send_broadcast(received_msg)
        
    except Exception as e:
        log(f"File reassembly failed: {e}")

def cleanup_incoming_files():
    """Remove unaccepted file entries after timeout"""
    while True:
        time.sleep(60)  
        with storage_lock:
            current_time = time.time()
            expired = []
            for fileid, file_rec in incoming_files.items():
                
                if not file_rec["received_chunks"] and current_time - file_rec["timestamp"] > 300:
                    expired.append(fileid)
            
            for fileid in expired:
                incoming_files.pop(fileid)
                log(f"Expired file offer: {fileid}")






def send_file(target: str, file_path: str, description: str = ""):
    try:
        import os
        
        # Debug information
        print(f"DEBUG: Current directory: {os.getcwd()}")
        print(f"DEBUG: Looking for file: '{file_path}'")
        print(f"DEBUG: Full path: '{os.path.abspath(file_path)}'")
        print(f"DEBUG: File exists: {os.path.exists(file_path)}")
        
        
        target_dir = os.path.dirname(file_path) if os.path.dirname(file_path) else "."
        print(f"DEBUG: Files in directory '{target_dir}':")
        try:
            for file in os.listdir(target_dir):
                if os.path.isfile(os.path.join(target_dir, file)):
                    full_path = os.path.join(target_dir, file)
                    size = os.path.getsize(full_path)
                    print(f"  - {file} ({size} bytes)")
        except Exception as e:
            print(f"  Error listing directory: {e}")
        
        if not os.path.exists(file_path):
            print("File not found")
            return

        filename = os.path.basename(file_path)
        filesize = os.path.getsize(file_path)
        fileid = hex(random.getrandbits(128))[2:]
        
        print(f"DEBUG: File found! Size: {filesize} bytes")
        
      
        timestamp = int(time.time())
        msg_id = hex(random.getrandbits(64))[2:]
        token = f"{USER_ID}|{timestamp+TTL_DEFAULT}|file"
        offer_msg = build_message({
            "TYPE": "FILE_OFFER",
            "FROM": USER_ID,
            "TO": target,
            "FILENAME": filename,
            "FILESIZE": filesize,
            "FILETYPE": "application/octet-stream",
            "FILEID": fileid,
            "DESCRIPTION": description,
            "TIMESTAMP": timestamp,
            "MESSAGE_ID": msg_id,
            "TOKEN": token
        })
        send_broadcast(offer_msg)
        print(f"File offer sent for {filename}. DEBUG: Waiting 20 seconds for acceptance...")

        time.sleep(20) 
        
        # Read and chunk file
        CHUNK_SIZE = 45000  # ~60KB after base64
        chunks = []
        with open(file_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                chunks.append(base64.b64encode(chunk).decode())
        
        total_chunks = len(chunks)
        print(f"DEBUG: File split into {total_chunks} chunks")
        
   
        for idx, data in enumerate(chunks):
            timestamp = int(time.time())
            msg_id = hex(random.getrandbits(64))[2:]
            token = f"{USER_ID}|{timestamp+TTL_DEFAULT}|file"
            chunk_msg = build_message({
                "TYPE": "FILE_CHUNK",
                "FROM": USER_ID,
                "TO": target,
                "FILEID": fileid,
                "CHUNK_INDEX": idx,
                "TOTAL_CHUNKS": total_chunks,
                "CHUNK_SIZE": len(data),
                "DATA": data,
                "TIMESTAMP": timestamp,
                "MESSAGE_ID": msg_id,
                "TOKEN": token
            })
            send_broadcast(chunk_msg)
            time.sleep(0.1)  # Prevent flooding
            
        print(f"Sent {filename} in {total_chunks} chunks")
        
    except Exception as e:
        print(f"File send failed: {e}")
        import traceback
        traceback.print_exc()

def send_group_create(group_name: str, members: str):
    """Create a new group with specified members"""
    try:
       
        group_id = f"group_{hex(random.getrandbits(64))[2:]}"
        
        # Include ourselves in te members list
        member_list = [USER_ID] + [m.strip() for m in members.split(",") if m.strip()]

        with storage_lock:
            groups[group_id] = {
                "name": group_name,
                "creator": USER_ID,
                "members": member_list
            }
        
        timestamp = int(time.time())
        message_id = hex(random.getrandbits(64))[2:]
        token = f"{USER_ID}|{timestamp + TTL_DEFAULT}|group"
        
        create_msg = build_message({
            "TYPE": "GROUP_CREATE",
            "FROM": USER_ID,
            "GROUP_ID": group_id,
            "GROUP_NAME": group_name,
            "MEMBERS": ",".join(member_list),
            "TIMESTAMP": timestamp,
            "MESSAGE_ID": message_id,
            "TOKEN": token
        })
        
        send_broadcast(create_msg)
        print(f"Created group '{group_name}' with ID: {group_id}")
        
    except Exception as e:
        print(f"Error creating group: {e}")

def send_group_message(group_id: str, message: str):
    """Send a message to a group"""
    try:
        # Check if we're a member of this group
        print(f"DEBUG: Checking membership for {USER_ID} in {groups[group_id]['members']}")
        if group_id not in groups or USER_ID not in groups[group_id]["members"]:
            print("You're not a member of this group")
            return

        # Prepare message fields
        timestamp = int(time.time())
        msg_id = hex(random.getrandbits(64))[2:]
        token = f"{USER_ID}|{timestamp+TTL_DEFAULT}|group"
        
        # Build the message
        group_msg = build_message({
            "TYPE": "GROUP_MESSAGE",
            "FROM": USER_ID,
            "GROUP_ID": group_id,
            "CONTENT": message,
            "TIMESTAMP": timestamp,
            "MESSAGE_ID": msg_id,
            "TOKEN": token
        })
        
        # Send the message
        send_broadcast(group_msg)
        log(f"Group message sent to {group_id}")
        
    except Exception as e:
        log(f"Error sending group message: {e}")
        raise

if __name__ == "__main__":
    threading.Thread(target=listen, args=(handle_message,), daemon=True).start()
    threading.Thread(target=periodic_broadcast, daemon=True).start()
    threading.Thread(target=cleanup_incoming_files, daemon=True).start()

    print("LSNP Peer started.")
    print("Commands: list, post <msg>, dm <user_id> <msg>, follow <user_id>, unfollow <user_id>, posts, dms, followers, verbose, exit, send_file <user_id> <file_path> [description], like <user_id> <post_timestamp>, unlike <user_id> <post_timestamp>, accept <fileid>")

    while True:
        cmd = input("> ").strip()

        if cmd == "list":
            print("Known Peers:")
            for uid, data in peers.items():
                print(f" - {data['display_name']} ({uid}): {data['status']}")

        elif cmd.startswith("post "):
            send_post(cmd[5:].strip())

        elif cmd.startswith("dm "):
            try:
                _, user_id, message = cmd.split(" ", 2)
                send_dm(user_id, message)
            except ValueError:
                print("Usage: dm <user_id> <message>")
        
        elif cmd.startswith("follow "):
            try:
                _, user_id = cmd.split(" ", 1)
                send_follow(user_id.strip())
            except ValueError:
                print("Usage: follow <user_id>")

        elif cmd.startswith("unfollow "):
            try:
                _, user_id = cmd.split(" ", 1)
                send_unfollow(user_id.strip())
            except ValueError:
                print("Usage: unfollow <user_id>")

        elif cmd == "verbose":
            config.VERBOSE = not config.VERBOSE
            print(f"Verbose mode {'ON' if config.VERBOSE else 'OFF'}")

        elif cmd == "posts":
            print("All Posts:")
            for p in posts:
                name = peers.get(p["user_id"], {}).get("display_name", p["user_id"])
                print(f" - {name}: {p['content']}")

        elif cmd == "dms":
            print("All DMs:")
            for m in dms:
                sender = peers.get(m["from"], {}).get("display_name", m["from"])
                print(f" - {sender}: {m['content']}")

        elif cmd == "followers":
            print("Followers:")
            for f in followers:
                name = peers.get(f, {}).get("display_name", f)
                print(f" - {name}")

        elif cmd == "groups":
            print("Groups:")
            for gid, gdata in groups.items():
                if USER_ID in gdata["members"]:
                    print(f" - {gdata['name']} ({gid}): {', '.join(gdata['members'])}")
        
        
        elif cmd.startswith("groupmsg "):
            try:
                parts = cmd.split(" ", 2)
                group_id = parts[1]
                message = parts[2]
                send_group_message(group_id, message)
            except ValueError:
                print("Usage: groupmsg <group_id> <message>")
            except Exception as e:
                print(f"Error sending group message: {e}")

        elif cmd.startswith("group_create "):
            try:
                parts = cmd.split(" ", 2)
                group_name = parts[1]
                members = parts[2]
                members = ",".join([m.strip() for m in members.split(",") if m.strip()])
                send_group_create(group_name, members)
            except ValueError:
                print("Usage: group_create <group_name> <member1,member2,...>")
        
        elif cmd.startswith("like "):
            try:
                _, user_id, post_timestamp = cmd.split(" ", 2)
                send_like(user_id.strip(), post_timestamp.strip(), "LIKE")

            except ValueError:
                print("Usage: like <user_id> <post_timestamp>")

        elif cmd.startswith("unlike "):
            try:
                _, user_id, post_timestamp = cmd.split(" ", 2)
                send_like(user_id.strip(), post_timestamp.strip(), "UNLIKE")
                
            except ValueError:
                print("Usage: unlike <user_id> <post_timestamp>")
        
        elif cmd.startswith("accept "):
            fileid = cmd.split(" ", 1)[1]
            with storage_lock:
                if fileid in incoming_files:
                    incoming_files[fileid]["accepted"] = True
                    incoming_files[fileid]["timestamp"] = time.time()
                    print(f"Accepting file transfer: {incoming_files[fileid]['filename']}")
                else:
                    print("File offer not found or expired")

        elif cmd.startswith("send_file "):
            parts = cmd.split(" ", 2)
            if len(parts) < 3:
                print("Usage: send_file <user> <filepath> [description]")
            else:
                threading.Thread(
                    target=send_file,
                    args=(parts[1], parts[2], parts[3] if len(parts)>3 else ""),
                    daemon=True
                ).start()
        elif cmd.startswith("ttt_invite "):
            try:
                _, target_user = cmd.split(" ", 1)
                from tictactoe import send_tictactoe_invite
                send_tictactoe_invite(target_user.strip())
            except ValueError:
                print("Usage: ttt_invite <user_id>")
        
        elif cmd.startswith("ttt_move "):
            try:
                parts = cmd.split(" ")
                game_id = parts[1]
                position = int(parts[2])
                from tictactoe import send_tictactoe_move
                send_tictactoe_move(game_id, position)
            except (ValueError, IndexError):
                print("Usage: ttt_move <game_id> <position>")
                print("Position: 0-8 (top-left to bottom-right)")
                print("0 | 1 | 2")
                print("3 | 4 | 5") 
                print("6 | 7 | 8")
        
        elif cmd == "ttt_games":
            from tictactoe import list_active_games
            list_active_games()
        
        elif cmd == "exit":
            print("Exiting LSNP peer...")
            break