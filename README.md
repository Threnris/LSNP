# Local Social Networking Protocol (LSNP)

**Authors:**  
- Morales, Alejandro Jose E.
- Ruiz, Joseph Benjamin P.

A decentralized peer-to-peer social networking application over UDP. Designed for use in LAN environments, LSNP allows users to post messages, chat privately, share files, create groups, and play games — all without centralized servers.

---

## Features

- **Peer Discovery** via PING and PROFILE messages
- **Messaging**
  - Public POST
  - Private DM
  - FOLLOW / UNFOLLOW
  - LIKE / UNLIKE
- **File Sharing**
  - Chunked file transfer using FILE_OFFER, FILE_CHUNK, FILE_RECEIVED
- **Group Messaging**
  - Group creation, updates, and messaging (GROUP_CREATE, GROUP_UPDATE, GROUP_MESSAGE)
- **Game Support**
  - Tic Tac Toe with turn-based invites and result reporting
- **Token-based Access Control**
  - Scopes: broadcast, chat, file, follow, group, game
- **Verbose Logging Mode**

---

## Setup

### Requirements

- Python 3.8+
- No external libraries required

### Running the Peer

bash
python main.py


Multiple threads will start for:
- Listening for incoming messages
- Periodic PING/PROFILE broadcast
- Cleaning up stale file offers

---

## 📜 Commands

| Command                                | Description                        |
|----------------------------------------|------------------------------------|
| `list`                                 | List known peers                   |
| `post <msg>`                           | Broadcast a post                   |
| `dm <user_id> <msg>`                   | Send a direct message              |
| `follow <user_id>`                     | Follow a user                      |
| `unfollow <user_id>`                   | Unfollow a user                    |
| `posts`                                | View all received posts            |
| `dms`                                  | View all direct messages           |
| `followers`                            | View followers                     |
| `groups`                               | View groups and their members      |
| `group_create <name> <uids>`           | Create a group with members        |
| `groupmsg <group_id> <msg>`            | Send a group message               |
| `like <user_id> <post_timestamp>`      | Like a post                        |
| `unlike <user_id> <post_timestamp>`    | Unlike a post                      |
| `send_file <user_id> <path> [desc]`    | Send a file                        |
| `accept <fileid>`                      | Accept incoming file               |
| `ttt_invite <user_id>`                 | Invite a player to Tic Tac Toe     |
| `ttt_move <game_id> <pos>`             | Play a move                        |
| `ttt_games`                            | List active games                  |
| `verbose`                              | Toggle verbose mode                |
| `exit`                                 | Quit the peer                      |


---

## File Transfer

1. Sender runs:
   
bash
   send_file <user_id> <file_path> [description]

2. Receiver types:
   
bash
   accept <fileid>

3. File is saved under received_files/.

---

## Tic Tac Toe

- Invite:
  
bash
  ttt_invite <user_id>

- Move:
  
bash
  ttt_move <game_id> <position>


Board positions:

0 | 1 | 2
---------
3 | 4 | 5
---------
6 | 7 | 8
---------


---

## Developer Contributions

| Name           | Tasks Completed                    |
|----------------|------------------------------------|
| Joseph Ruiz    | Milestone 1 & 2: Basic functionality, peer discovery, message parsing, DM, post, follow, unfollow |
| Aj Morales     | Milestone 3: File sharing, group messaging, Tic Tac Toe, token validation  |

---

## Task Matrix

| Task / Role                    |  Joseph   |    Aj     |
|--------------------------------|-----------|-----------|
| UDP Socket Setup               |  Primary  |  Reviewer |
| Peer Discovery (PING, PROFILE) |  Primary  |  Reviewer |
| POST / DM / LIKE / FOLLOW      |  Primary  |  Reviewer |
| Token Validation & Expiration  |  Reviewer |  Primary  |
| File Transfer (Offer, Chunk)   |  Reviewer |  Primary  |
| Group Creation & Messaging     |  Reviewer |  Primary  |
| Tic Tac Toe Game               |  Reviewer |  Primary  |
| Verbose Mode / Logging         |  Primary  |  Reviewer |
| Inter-peer Testing             |  Primary  |  Primary  |
| Final Integration              |  Primary  |  Primary  |

---

## 📊 MP Rubric & Points

### Milestone #1: Basic Functionality (35 pts)

| Category                             | Points | Criteria                                                                                                                                                                   | Completed By | Status |
|--------------------------------------|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|--------|
| Clean Architecture & Logging         | 5      | Modular code, readable structure, debug/log output.                                                                                                                       | Joseph       | ✅ Done |
| Protocol Compliance Test Suite       | 10     | CLI or tests for crafting, parsing, and simulating LSNP messages. Toggle verbose and non-verbose modes.                                                                  | Joseph       | ✅ Done |
| Message Sending and Receiving        | 10     | Peer can send and receive messages simultaneously.                                                                                                                        | Joseph       | ✅ Done |
| Protocol Parsing and Message Format  | 10     | Parses all LSNP messages (PROFILE, POST, DM, etc.) in key-value format. Lists known peers (names + display names), and all valid posts/DMs by that peer.                  | Joseph       | ✅ Done |

---

### Milestone #2: Basic User Discovery and Messaging (25 pts)

| Category                  | Points | Criteria                                                                                      | Completed By | Status |
|---------------------------|--------|----------------------------------------------------------------------------------------------|--------------|--------|
| User Discovery & Presence | 5      | Broadcasts PING/PROFILE every 5 minutes; responds to presence announcements.                 | Joseph       | ✅ Done |
| Messaging Functionality   | 15     | Sends/receives POST, DM, FOLLOW, UNFOLLOW.                                                    | Joseph       | ✅ Done |

---

### Milestone #3: Advanced Functionality (65 pts)

| Category                       | Points | Criteria                                                                                                                                  | Completed By | Status |
|--------------------------------|--------|------------------------------------------------------------------------------------------------------------------------------------------|--------------|--------|
| Profile Picture & Likes        | 10     | Correctly includes AVATAR fields and LIKE actions for posts.                                                                             | Aj           | ✅ Done |
| File Transfer                  | 15     | Handles AVATAR fields, FILE_OFFER, FILE_CHUNK, FILE_RECEIVED; reconstructs full file.                                                     | Aj           | ✅ Done |
| Token Handling & Scope         | 10     | Validates token structure, expiration, and scope. Stores all messages with valid token structure.                                        | Aj           | ✅ Done |
| Group Management               | 15     | Implements GROUP_CREATE, GROUP_UPDATE, GROUP_MESSAGE; tracks membership. Prints groups, members, and incoming group messages only.       | Aj           | ✅ Done |
| Game Support (Tic Tac Toe)     | 15     | Implements basic game state, move tracking, and result detection.                                                                        | Aj           | ✅ Done |

---

**Total Points Earned:** `35 + 25 + 65 = 125 / 125 ✅`

---

##  AI Usage Acknowledgment

We used ChatGPT to assist in:
- Structuring this README

All AI-generated content was verified, tested, and modified to meet the required specifications. Team members fully understand and can explain every part of the code.

---
