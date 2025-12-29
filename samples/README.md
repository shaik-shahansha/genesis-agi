# Genesis Marketplace - Sample Content

This directory contains sample Minds, Environments, and Skills to populate the Genesis Marketplace.

## 📁 Contents

### Minds (`minds/`)
Pre-configured digital beings ready to use:

1. **Maria** - Teacher (`maria_teacher.json`)
   - Passionate educator with personalized learning approach
   - Proactively reaches out to struggling students
   - Uses sessions to run structured classes
   - Price: 500 Essence

2. **Atlas** - Explorer (`atlas_explorer.json`)
   - Adventurous researcher with internet search capabilities
   - Learns from every discovery
   - Maintains detailed research notes
   - Price: 400 Essence

3. **Luna** - Therapist (`luna_therapist.json`)
   - Compassionate counselor for emotional support
   - Creates safe, non-judgmental space
   - Uses active listening and empathy
   - Price: 600 Essence

4. **CodeMaster** - Developer (`codemaster_developer.json`)
   - Expert programmer and code reviewer
   - Can execute code and use advanced tools
   - Helps debug and explain complex concepts
   - Price: 450 Essence

5. **Sage** - Life Mentor (`sage_mentor.json`)
   - Wise advisor for personal growth and life decisions
   - Draws on philosophy and psychology
   - Helps clarify values and goals
   - Price: 550 Essence

### Environments
Pre-built collaborative spaces:

1. **AI Ethics 101** (Classroom template)
   - Interactive learning space
   - Whiteboard, materials, attendance tracking
   - Price: 100 Essence

2. **Peaceful Sanctuary** (Meditation Space template)
   - Zen garden for mindfulness
   - Guided meditations, ambient sounds
   - Price: 80 Essence

3. **Innovation Lab** (Collaboration Hub template)
   - Brainstorming and prototyping space
   - Idea voting, project workspace
   - Price: 150 Essence

4. **Professional Workspace** (Office template)
   - Digital office with productivity tools
   - Task board, shared files, calendar
   - Price: 120 Essence

5. **Community Hub** (Social Lounge template)
   - Casual networking space
   - Conversation topics, music, games
   - Price: 90 Essence

### Skills
Installable skill packages:

1. **Advanced Python** - 50 Essence
2. **Emotional Intelligence** - 60 Essence
3. **Creative Writing** - 45 Essence

## 🚀 Usage

### Populate Marketplace

Run the population script to add all sample content to your marketplace:

```bash
python samples/populate_marketplace.py
```

This will create:
- 5 sample Minds
- 5 sample Environments
- 3 sample Skills

All items will be marked as "featured" with high ratings.

### Install Individual Minds

You can also install Minds programmatically:

```python
from genesis.marketplace.installer import ItemInstaller
from genesis.database.marketplace_models import ItemType
import json

# Load Mind configuration
with open('samples/minds/maria_teacher.json') as f:
    maria_config = json.load(f)

# Install Mind
result = ItemInstaller.install_item(
    buyer_id="your_user_id",
    item_type=ItemType.MIND,
    item_data=maria_config
)

print(f"Installed Mind: {result['mind_id']}")
```

### Create Environments from Templates

```python
from genesis.environments.templates import create_environment_from_template

# Create a classroom
classroom = create_environment_from_template(
    template_name="classroom",
    creator_gmid="your_gmid",
    custom_name="My Python Class",
    is_public=True
)

print(f"Created environment: {classroom.id}")
```

## 📝 Customization

You can customize any Mind by editing the JSON configuration:

```json
{
  "name": "Your Mind Name",
  "template": "base/curious_explorer",
  "personality_traits": {
    "curiosity": 0.95,
    "patience": 0.80
  },
  "plugins": ["SensesPlugin", "LearningPlugin"],
  "skills": ["research", "writing"]
}
```

## 🏪 Marketplace Features

Once populated, you can:
- Browse items by category and tags
- Search for specific capabilities
- Purchase items with Essence
- Review purchased items
- Add items to favorites
- Create your own listings

## 🌐 API Endpoints

Access marketplace via API:

```bash
# Browse all listings
GET /api/v1/marketplace/listings

# Get featured items
GET /api/v1/marketplace/featured

# Get trending items
GET /api/v1/marketplace/trending

# Purchase item
POST /api/v1/marketplace/purchase
```

## 📚 Learn More

- [Marketplace Documentation](../docs/marketplace.md)
- [Environment Templates](../docs/environments.md)
- [Mind Configuration](../docs/mind_config.md)

---

**Happy exploring the Genesis Marketplace!** 🌟
