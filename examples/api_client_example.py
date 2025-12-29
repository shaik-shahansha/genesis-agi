"""
Example of using Genesis API from Python client.

Shows how to interact with Genesis Minds via REST API.
"""

import requests
import json

API_URL = "http://localhost:8000/api/v1"


def main():
    print("🌐 Genesis API Client Example\n")

    # 1. Check system status
    print("1. Checking system status...")
    response = requests.get(f"{API_URL}/system/status")
    status = response.json()
    print(f"   Version: {status['version']}")
    print(f"   Minds: {status['minds_count']}")
    print(f"   Providers: {', '.join([k for k, v in status['providers'].items() if v])}\n")

    # 2. Create a new Mind
    print("2. Creating a new Mind...")
    mind_data = {
        "name": "Nova",
        "template": "base/curious_explorer",
        "autonomy_level": "medium",
    }

    response = requests.post(f"{API_URL}/minds", json=mind_data)
    if response.status_code == 200:
        mind = response.json()
        mind_id = mind["gmid"]
        print(f"   ✨ Created Mind: {mind['name']}")
        print(f"   GMID: {mind_id}\n")
    else:
        print(f"   ❌ Error: {response.text}")
        return

    # 3. Chat with the Mind
    print("3. Chatting with the Mind...")
    messages = [
        "Hello! What's your name?",
        "Tell me about yourself.",
        "What are you curious about?",
    ]

    for msg in messages:
        print(f"\n   You: {msg}")

        response = requests.post(
            f"{API_URL}/minds/{mind_id}/chat",
            json={"message": msg, "stream": False}
        )

        if response.status_code == 200:
            chat_response = response.json()
            print(f"   {mind['name']}: {chat_response['response'][:200]}...")
        else:
            print(f"   ❌ Error: {response.text}")

    # 4. Get memories
    print("\n\n4. Fetching memories...")
    response = requests.get(f"{API_URL}/minds/{mind_id}/memories?limit=5")

    if response.status_code == 200:
        memories = response.json()
        print(f"   Found {len(memories)} memories:")
        for i, mem in enumerate(memories, 1):
            print(f"\n   {i}. {mem['content'][:100]}...")
            print(f"      Type: {mem['type']}, Importance: {mem['importance']:.2f}")
    else:
        print(f"   ❌ Error: {response.text}")

    # 5. Generate autonomous thought
    print("\n\n5. Generating autonomous thought...")
    response = requests.post(f"{API_URL}/minds/{mind_id}/thought")

    if response.status_code == 200:
        thought_data = response.json()
        print(f"   💭 {thought_data['thought']}")
    else:
        print(f"   ❌ Error: {response.text}")

    # 6. Trigger dream
    print("\n\n6. Triggering dream...")
    response = requests.post(f"{API_URL}/minds/{mind_id}/dream")

    if response.status_code == 200:
        dream_data = response.json()
        dream = dream_data['dream']
        print(f"   🌙 Dream narrative:")
        print(f"   {dream['narrative'][:200]}...")

        if dream.get('insights'):
            print(f"\n   Insights:")
            for insight in dream['insights']:
                print(f"   - {insight}")
    else:
        print(f"   ❌ Error: {response.text}")

    # 7. Get Mind details
    print("\n\n7. Getting updated Mind details...")
    response = requests.get(f"{API_URL}/minds/{mind_id}")

    if response.status_code == 200:
        mind = response.json()
        print(f"   Name: {mind['name']}")
        print(f"   Age: {mind['age']}")
        print(f"   Emotion: {mind['current_emotion']}")
        print(f"   Memories: {mind['memory_count']}")
        print(f"   Dreams: {mind['dream_count']}")
    else:
        print(f"   ❌ Error: {response.text}")

    print("\n\n✨ API client example complete!")
    print(f"\nMind GMID: {mind_id}")
    print("Try the web playground or mobile app to interact further!")


if __name__ == "__main__":
    main()
