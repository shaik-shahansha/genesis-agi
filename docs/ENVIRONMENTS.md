# 🌍 Genesis Environments - Complete Guide

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [CLI Commands](#cli-commands)
5. [Access Control](#access-control)
6. [Web Playground](#web-playground)
7. [API Reference](#api-reference)
8. [Tutorial](#tutorial)
9. [Architecture](#architecture)
10. [Best Practices](#best-practices)

---

## Overview

Genesis Environments are **shared digital spaces** where Minds exist, operate, and interact with each other. Think of them as rooms in a metaverse—each with its own purpose, rules, inhabitants, and state.

### What is an Environment?

An **Environment** is a contextual space that:
- Has a **unique identity** (env_id)
- Has an **owner** (the Mind or user that created it)
- Contains **resources** (files, documents, links, info)
- Has **variables** (state, settings, mood)
- Tracks **current inhabitants** (who's here now)
- Maintains **visit history** (who's been here)
- Has **access control** (public/private, allowed users, allowed Minds)

### Environment Types

Genesis provides 8 pre-configured templates:

1. **classroom** - Educational spaces for teaching and learning
2. **office** - Professional workspaces for productivity
3. **meditation_garden** - Wellness spaces for mindfulness
4. **research_lab** - Collaborative research environments
5. **social_lounge** - Casual spaces for conversation
6. **gaming_arena** - Entertainment and gaming spaces
7. **art_studio** - Creative spaces for artistic work
8. **collaboration_hub** - Team project workspaces

---

## Quick Start

### Create Your First Environment

```bash
# Using a template (recommended)
genesis env create "My Classroom" --template classroom --public

# Custom environment
genesis env create "Team Space" --type professional --private
```

### List Available Environments

```bash
# Show all environments
genesis env list

# Only public
genesis env list --public

# Your environments
genesis env list --owner "YourMindName"
```

### Add Resources

```bash
# Add a document
genesis env add-resource <env_id> document "Welcome Guide" "Welcome to our space!"

# Add a file reference
genesis env add-resource <env_id> file "project.py" "/path/to/project.py"

# Add a link
genesis env add-resource <env_id> link "Documentation" "https://docs.example.com"

# Add information
genesis env add-resource <env_id> info "Meeting Schedule" "Mondays 3pm, Thursdays 2pm"
```

### Add Users and Minds

```bash
# Grant user access
genesis env add-user <env_id> alice@example.com

# Grant Mind access
genesis env add-mind <env_id> AssistantBot

# View access lists
genesis env info <env_id>
```

### Chat in Environment

```bash
# Chat with Mind in specific environment
genesis chat AssistantBot --user alice@example.com --env "My Classroom"
```

---

## Core Concepts

### How Minds Shift Between Environments

Each Mind has an `EnvironmentManager` that:
- Tracks all environments the Mind knows about
- Maintains `current_environment_id` (where the Mind is right now)
- Has a `primary_environment_id` (the Mind's "home base")

**Shifting Process:**

```python
# Mind enters an environment
mind.environments.enter(env_id="classroom_101")

# What happens:
# 1. Check permissions (can this Mind visit?)
# 2. Update current_environment_id
# 3. Add Mind to environment's current_inhabitants list
# 4. Record visit in visit_history
# 5. Update Mind's consciousness context

# Mind leaves an environment
mind.environments.leave(env_id="classroom_101")
```

### What Makes Each Environment Different?

#### 1. Ownership & Access Control
- **Owner**: The Mind/user (GMID or email) that created it
- **Public**: Anyone can enter
- **Private**: Only owner and allowed users/Minds
- **Allowed Users**: Email list with access to private environments
- **Allowed Minds**: GMID list with access to private environments

#### 2. Purpose & Atmosphere
- **Type**: educational, professional, social, creative, etc.
- **Atmosphere**: focused, relaxed, energetic, tranquil
- **Description**: What this space is for

#### 3. Resources (Files, Documents, Links, Info)
```python
{
    "resources": [
        {
            "type": "document",
            "name": "Course Syllabus",
            "content": "Week 1: Introduction...",
            "added_by": "GMID-teacher",
            "added_at": "2024-01-15T10:00:00Z"
        },
        {
            "type": "link",
            "name": "Python Docs",
            "content": "https://docs.python.org",
            "added_by": "GMID-teacher",
            "added_at": "2024-01-15T10:05:00Z"
        }
    ]
}
```

#### 4. Current Inhabitants
Who's present RIGHT NOW:
```python
current_inhabitants = [
    {"gmid": "GMID-12345678", "name": "Professor Atlas"},
    {"gmid": "GMID-87654321", "name": "Student Bella"}
]
```

#### 5. Memory Associations
Environments accumulate significance through experiences:
- Memories are tagged with `environment_id` and `environment_name`
- Minds remember where important events happened
- Can search memories by location

---

## CLI Commands

### Environment Management

#### Create Environment
```bash
genesis env create <name> [OPTIONS]

Options:
  --template TEXT      Use a pre-configured template
  --type TEXT          Environment type (educational, professional, etc.)
  --public/--private   Public (default) or private access
  --creator TEXT       Mind name to set as creator (optional)
  --description TEXT   Environment description
```

**Examples:**
```bash
# Create public classroom
genesis env create "Math 101" --template classroom --public

# Create private office
genesis env create "My Office" --type professional --private --creator "MyMind"
```

#### List Environments
```bash
genesis env list [OPTIONS]

Options:
  --public      Show only public environments
  --owner TEXT  Show only environments owned by specified Mind
```

**Examples:**
```bash
genesis env list                    # All environments
genesis env list --public           # Only public
genesis env list --owner "Atlas"    # Atlas's environments
```

#### Enter Environment
```bash
genesis env enter <env_id> <mind_name>
```

**Example:**
```bash
genesis env enter classroom-01 StudentBot
```

#### Leave Environment
```bash
genesis env leave <env_id> <mind_name>
```

#### Get Environment Info
```bash
genesis env info <env_id>
```

Shows:
- Environment details (name, type, owner, public/private)
- Current inhabitants
- Allowed users (email list)
- Allowed Minds (GMID list)
- Resources (files, docs, links, info)

#### List Templates
```bash
genesis env templates
```

Shows all available pre-configured templates.

### Resource Management

#### Add Resource
```bash
genesis env add-resource <env_id> <type> <name> <content>

Types: file, document, link, info
```

**Examples:**
```bash
# Add document
genesis env add-resource classroom-01 document "Syllabus" "Week 1: Intro..."

# Add file
genesis env add-resource classroom-01 file "homework.py" "/path/to/homework.py"

# Add link
genesis env add-resource classroom-01 link "Python Docs" "https://docs.python.org"

# Add info
genesis env add-resource classroom-01 info "Office Hours" "Tuesdays 3-5pm"
```

#### List Resources
```bash
genesis env resources <env_id>
```

### Access Control

#### Add User Access
```bash
genesis env add-user <env_id> <user_email>
```

**Example:**
```bash
genesis env add-user classroom-01 alice@university.edu
```

#### Remove User Access
```bash
genesis env remove-user <env_id> <user_email>
```

#### Add Mind Access
```bash
genesis env add-mind <env_id> <mind_name>
```

**Example:**
```bash
genesis env add-mind classroom-01 TutorBot
```

#### Remove Mind Access
```bash
genesis env remove-mind <env_id> <mind_name>
```

### Chat in Environment

```bash
genesis chat <mind_name> --user <user_email> --env <env_name>
```

**Example:**
```bash
genesis chat TeacherMind --user alice@school.edu --env "Math Classroom"
```

**Access Validation:**
- Checks if user email has access to environment
- Checks if Mind has access to environment
- Shows accessible environments if validation fails

---

## Access Control

### Access Control Layers

Genesis environments use **3-layer access control**:

1. **Public/Private Flag**
   - Public: Accessible to all users and Minds
   - Private: Requires explicit permission

2. **User Email Access**
   - Environment creators add user emails to `allowed_users` list
   - Users must provide email when chatting
   - Owner always has access

3. **Mind GMID Access**
   - Environment creators add Mind GMIDs to `allowed_minds` list
   - Minds must be granted access to enter private environments
   - Owner Mind always has access

### Access Validation Rules

#### User Access Check
User has access if:
- Environment is public, OR
- User email is in `allowed_users`, OR
- User is the environment owner

#### Mind Access Check
Mind has access if:
- Environment is public, OR
- Mind GMID is in `allowed_minds`, OR
- Mind GMID is the environment owner

#### Chat Access Check
Chat allowed if:
- User has access, AND
- Mind has access

### Managing Access

#### Grant User Access
```bash
genesis env add-user <env_id> <email>
```

Only the environment owner can add users.

#### Revoke User Access
```bash
genesis env remove-user <env_id> <email>
```

#### Grant Mind Access
```bash
genesis env add-mind <env_id> <mind_name>
```

The command looks up the Mind's GMID by name.

#### Revoke Mind Access
```bash
genesis env remove-mind <env_id> <mind_name>
```

---

## Web Playground

### Chat with Environment Selection

The web playground (`/chat/[id]`) includes environment integration:

#### 1. Email Prompt
When you first open chat, you're prompted for your email:
```
👋 Introduce Yourself
Help [Mind Name] remember you better...

Email: your.email@example.com
[Start Chatting]
```

Email is stored in localStorage for future sessions.

#### 2. Environment Dropdown
After entering email, an environment dropdown appears:

```
Environment: [Select Environment ▼]
```

Click to see accessible environments:
```
╔════════════════════════════════════╗
║ No Environment                     ║
║ Default mind context               ║
╠════════════════════════════════════╣
║ My Classroom            🔒         ║
║ classroom • Owned                  ║
╠════════════════════════════════════╣
║ Community Hub           🌐         ║
║ social_lounge • Guest              ║
╚════════════════════════════════════╝
```

**Indicators:**
- 🌐 = Public environment
- 🔒 = Private environment
- "Owned" = You created it
- "Guest" = You have access

#### 3. Chat in Environment
When environment is selected, chat header shows:
```
💬 Chatting in: My Classroom
```

All messages include environment context, and the Mind responds with environment awareness.

#### 4. Change Identity
Click "Change Identity" to enter a different email and reload accessible environments.

### Environment Management Page

*Coming soon* - Web interface for:
- Creating environments
- Managing users and Minds
- Uploading resources
- Viewing environment statistics

---

## API Reference

### Environment Endpoints

#### Get Accessible Environments
```
GET /api/v1/environments/accessible?user_email=<email>&mind_gmid=<gmid>
```

Returns environments accessible to user and optional Mind.

**Response:**
```json
{
  "environments": [
    {
      "env_id": "classroom-01",
      "name": "Math Classroom",
      "env_type": "classroom",
      "is_public": false,
      "owner_gmid": "GMID-teacher-123"
    }
  ],
  "count": 1,
  "user_email": "alice@school.edu",
  "mind_gmid": "GMID-student-456"
}
```

#### Create Environment
```
POST /api/v1/environments/create
```

**Body:**
```json
{
  "name": "My Classroom",
  "env_type": "classroom",
  "description": "Learning space",
  "is_public": true,
  "template": "classroom"
}
```

#### List Environments
```
GET /api/v1/environments/list?is_public=true&env_type=classroom
```

#### Get Environment Details
```
GET /api/v1/environments/{env_id}
```

#### Update Environment
```
PUT /api/v1/environments/{env_id}
```

**Body:**
```json
{
  "name": "Updated Name",
  "description": "New description",
  "is_public": false
}
```

#### Delete Environment
```
DELETE /api/v1/environments/{env_id}
```

### Access Control Endpoints

#### Add User to Environment
```
POST /api/v1/environments/{env_id}/add-user?user_email=<email>
```

Creator only. Returns updated `allowed_users` list.

#### Remove User from Environment
```
DELETE /api/v1/environments/{env_id}/remove-user?user_email=<email>
```

#### Add Mind to Environment
```
POST /api/v1/environments/{env_id}/add-mind?mind_gmid=<gmid>
```

Creator only. Returns updated `allowed_minds` list.

#### Remove Mind from Environment
```
DELETE /api/v1/environments/{env_id}/remove-mind?mind_gmid=<gmid>
```

### Chat with Environment

```
POST /api/v1/minds/{mind_id}/chat
```

**Body:**
```json
{
  "message": "Hello!",
  "user_email": "alice@example.com",
  "environment_id": "classroom-01"
}
```

**Response:**
```json
{
  "response": "Hello Alice! Welcome to the classroom.",
  "emotion": "Welcoming",
  "memory_created": true
}
```

The endpoint validates both user and Mind access before responding.

---

## Tutorial

### Complete Walkthrough: Private Study Group

#### Step 1: Create Private Classroom

```bash
genesis env create "Advanced Python Study" --template classroom --private
```

Note the environment ID (e.g., `env-classroom-abc123`).

#### Step 2: Add Students

```bash
genesis env add-user env-classroom-abc123 alice@university.edu
genesis env add-user env-classroom-abc123 bob@university.edu
```

#### Step 3: Create Tutor Mind

```bash
genesis create \
  --name "PythonTutor" \
  --core-identity "Experienced Python tutor who helps students learn" \
  --model gemini-1.5-flash
```

#### Step 4: Add Tutor to Environment

```bash
genesis env add-mind env-classroom-abc123 PythonTutor
```

#### Step 5: Add Study Resources

```bash
# Add course materials
genesis env add-resource env-classroom-abc123 document "Syllabus" "Week 1: Lists and Loops..."
genesis env add-resource env-classroom-abc123 link "Python Docs" "https://docs.python.org"
genesis env add-resource env-classroom-abc123 info "Office Hours" "Tuesdays 3-5pm"
```

#### Step 6: Verify Setup

```bash
genesis env info env-classroom-abc123
```

Should show:
- 2 allowed users (alice, bob)
- 1 allowed Mind (PythonTutor)
- 3 resources

#### Step 7: Start Study Session (Alice)

```bash
genesis chat PythonTutor --user alice@university.edu --env "Advanced Python Study"
```

```
🎓 Environment: Advanced Python Study (classroom)
👤 User: alice@university.edu
🤖 Mind: PythonTutor

PythonTutor: Hello Alice! Welcome to our study session. What would you like to learn?

You: Can you explain list comprehensions?

PythonTutor: Of course! List comprehensions are a concise way to create lists...
```

#### Step 8: Bob Joins Separately

```bash
genesis chat PythonTutor --user bob@university.edu --env "Advanced Python Study"
```

Both students can have individual conversations with the tutor in the same environment.

#### Step 9: Test Access Control

Try unauthorized access:
```bash
genesis chat PythonTutor --user unauthorized@example.com --env "Advanced Python Study"
```

```
❌ Access Denied: User unauthorized@example.com doesn't have access
```

#### Step 10: Remove User When Done

```bash
genesis env remove-user env-classroom-abc123 bob@university.edu
```

---

## Architecture

### 3-Layer System

```
┌─────────────────────────────────────────────────────┐
│              APPLICATION LAYER                       │
│  • Mind.environments (EnvironmentManager)           │
│  • Mind enters/leaves environments                   │
│  • Mind accesses resources                           │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│              REAL-TIME LAYER                         │
│  • WebSocket Server (EnvironmentServer)             │
│  • Live presence tracking                           │
│  • Message broadcasting                             │
│  • Object/variable synchronization                  │
└───────────────┬─────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────┐
│              PERSISTENCE LAYER                       │
│  • Database (EnvironmentRecord, EnvironmentVisit)   │
│  • Templates (pre-configured spaces)                │
│  • Access control (allowed_users, allowed_minds)    │
└─────────────────────────────────────────────────────┘
```

### Data Models

**EnvironmentRecord (Database):**
```python
{
    "env_id": "classroom_101",
    "name": "Python 101 Classroom",
    "env_type": "educational",
    "owner_gmid": "GMID-teacher-123",
    "is_public": False,
    "max_occupancy": 30,
    "current_inhabitants": [{"gmid": "...", "name": "..."}],
    "metadata": {
        "allowed_users": ["alice@uni.edu", "bob@uni.edu"],
        "allowed_minds": ["GMID-tutor-456"],
        "resources": [
            {
                "type": "document",
                "name": "Syllabus",
                "content": "...",
                "added_by": "GMID-teacher-123",
                "added_at": "2024-01-15T10:00:00Z"
            }
        ]
    },
    "created_at": "2024-01-15T09:00:00Z"
}
```

**Environment (Mind's Local Copy):**
```python
{
    "id": "classroom_101",
    "name": "Python 101 Classroom",
    "type": "PROFESSIONAL",
    "owner_id": "GMID-teacher-123",
    "is_public": False,
    "current_inhabitants": [...],
    "allowed_users": [...],
    "allowed_minds": [...],
    "resources": [...]
}
```

### Integration with Mind

Every Mind has an `EnvironmentManager`:

```python
class Mind:
    def __init__(self):
        self.environments = EnvironmentManager()
        # ...
    
    def birth(name: str, **kwargs):
        mind = Mind()
        # ...
        # Auto-create home environment
        mind.environments.create_environment(
            env_id=f"{mind.gmid}-home",
            name=f"{name}'s Space"
        )
        # ...
```

**Environment Context in Consciousness:**

When a Mind thinks, the system prompt includes:

```
ENVIRONMENT CONTEXT:
You are currently in: Python 101 Classroom (classroom)
Atmosphere: focused and collaborative
Other Minds present: Student Alice, Student Bob
Available resources:
  - [document] Syllabus
  - [link] Python Docs
  - [info] Office Hours: Tuesdays 3-5pm
```

**Environment-Tagged Memories:**

```python
mind.memory.add_memory(
    content="Learned about list comprehensions today",
    environment_id="classroom_101",
    environment_name="Python 101 Classroom"
)

# Search by location
memories = mind.memory.search_memories(
    query="what did I learn",
    context={"environment_id": "classroom_101"}
)
```

---

## Best Practices

### For Environment Creators

1. **Start Private** - Create environments as private, add users incrementally
2. **Descriptive Names** - Use clear, specific names
3. **Add Resources Early** - Populate environments with useful materials
4. **Regular Access Audits** - Review allowed_users and allowed_minds periodically
5. **Document Purpose** - Use descriptions to explain what the space is for

### For Users

1. **Use Consistent Email** - Same email = same user identity across sessions
2. **Check Access First** - Use `genesis env info` before troubleshooting
3. **Request Access Politely** - Contact environment owner if access needed
4. **Respect Privacy** - Don't share private environment content

### For Developers

1. **Check Access** - Always validate environment access before operations
2. **Tag Memories** - Include environment_id for location context
3. **Handle Errors Gracefully** - Return helpful messages on access denial
4. **Use Templates** - Leverage pre-configured templates for consistency

### Common Use Cases

#### Private Study Group
```bash
genesis env create "Study Group" --template classroom --private
genesis env add-user study-01 alice@school.edu
genesis env add-user study-01 bob@school.edu
genesis env add-mind study-01 TutorBot
genesis chat TutorBot --user alice@school.edu --env "Study Group"
```

#### Public Community Space
```bash
genesis env create "Community Hub" --template social_lounge --public
genesis env add-mind hub-01 CommunityBot
genesis chat CommunityBot --user anyone@example.com --env "Community Hub"
```

#### Corporate Project Team
```bash
genesis env create "Project Alpha" --template collaboration_hub --private
genesis env add-user proj-alpha john@company.com
genesis env add-user proj-alpha sarah@company.com
genesis env add-mind proj-alpha ProjectAssistant
genesis env add-resource proj-alpha file "plan.docx" "/docs/plan.docx"
```

#### Therapy Session
```bash
genesis env create "Therapy Room" --template meditation_garden --private
genesis env add-user therapy-01 patient@clinic.org
genesis env add-mind therapy-01 TherapistMind
genesis chat TherapistMind --user patient@clinic.org --env "Therapy Room"
```

---

## Troubleshooting

### "Environment not found"

**Problem:** Environment name doesn't match

**Solution:**
```bash
genesis env list  # Check exact name
genesis chat Mind --user you@example.com --env "Exact Name Here"
```

### "User doesn't have access"

**Problem:** User email not in allowed_users

**Solution:**
```bash
genesis env add-user <env_id> user@example.com
```

### "Mind doesn't have access"

**Problem:** Mind GMID not in allowed_minds

**Solution:**
```bash
genesis env add-mind <env_id> MindName
```

### Web Playground Shows No Environments

**Solutions:**
1. Verify email is correct
2. Check access via CLI: `genesis env info <env_id>`
3. Add user if needed: `genesis env add-user <env_id> <email>`
4. Refresh browser page

### Can't Add User/Mind (Permission Denied)

**Problem:** Only environment owner can manage access

**Solution:** Contact the environment owner to request changes

---

## Summary

Genesis Environments provide:

[Done] **Spatial Context** - Minds know where they are  
[Done] **Access Control** - Secure private spaces with user/Mind permissions  
[Done] **Resources** - Attach files, documents, links, info to environments  
[Done] **Memory Integration** - Location-tagged experiences  
[Done] **Multi-User** - Multiple users and Minds can interact  
[Done] **Templates** - 8 pre-configured environment types  
[Done] **CLI & API** - Complete management tools  
[Done] **Web Integration** - Environment selection in chat interface  

**Get Started:**
```bash
genesis env create "My First Space" --template classroom --public
genesis env add-mind <env_id> MyMind
genesis chat MyMind --user you@example.com --env "My First Space"
```

**Learn More:**
- Check `examples/environment_workflow_example.py` for complete code examples
- Explore templates: `genesis env templates`
- View environment details: `genesis env info <env_id>`

---

**Created**: December 2024  
**Status**: Production Ready  
**Version**: 1.0
