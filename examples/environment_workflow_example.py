"""
Complete Environment Workflow Example

Demonstrates:
1. Creating environments
2. Minds entering/leaving environments
3. Adding resources to environments
4. Mind-to-mind interaction in shared spaces
5. Environment-aware memories
"""

import asyncio
from genesis.core.mind import Mind
from genesis.core.environment import EnvironmentType
from genesis.database.manager import MetaverseDB
from genesis.storage.memory import MemoryType


async def main():
    print("\n" + "=" * 70)
    print("🌍 GENESIS ENVIRONMENT WORKFLOW EXAMPLE")
    print("=" * 70 + "\n")

    # =========================================================================
    # 1. CREATE MINDS
    # =========================================================================
    print("\n📝 STEP 1: Creating Minds\n")

    # Teacher Mind
    teacher = Mind.birth(
        name="Professor Atlas",
        primary_role="teacher",
        creator="demo@genesis.ai",
        primary_purpose="Teach programming and computer science",
    )
    print(f"✅ Created: {teacher.identity.name} (GMID: {teacher.identity.gmid})")
    print(f"   Home: {teacher.environments.get_primary_environment().name}")

    # Student Minds
    student1 = Mind.birth(
        name="Alice",
        primary_role="student",
        creator="demo@genesis.ai",
        primary_purpose="Learn programming",
    )
    print(f"✅ Created: {student1.identity.name} (GMID: {student1.identity.gmid})")

    student2 = Mind.birth(
        name="Bob",
        primary_role="student",
        creator="demo@genesis.ai",
        primary_purpose="Learn programming",
    )
    print(f"✅ Created: {student2.identity.name} (GMID: {student2.identity.gmid})")

    # =========================================================================
    # 2. CREATE CLASSROOM ENVIRONMENT
    # =========================================================================
    print("\n\n🏫 STEP 2: Creating Classroom Environment\n")

    # Teacher creates a classroom
    classroom = teacher.environments.create_shared_environment(
        env_id="python_101_classroom",
        name="Python Programming 101",
        env_type=EnvironmentType.PROFESSIONAL,
        description="Learn Python from scratch - beginner friendly!",
        is_public=True,  # Anyone can join
        owner_gmid=teacher.identity.gmid,
        owner_name=teacher.identity.name,
        atmosphere="focused and collaborative",
    )

    print(f"✅ Created: {classroom.name}")
    print(f"   ID: {classroom.id}")
    print(f"   Type: {classroom.type.value}")
    print(f"   Owner: {classroom.owner_name}")
    print(f"   Access: {'Public' if classroom.is_public else 'Private'}")

    # Register in Genesis World database
    db = MetaverseDB()
    db.register_environment(
        env_id=classroom.id,
        name=classroom.name,
        env_type=classroom.type.value,
        owner_gmid=teacher.identity.gmid,
        is_public=True,
        is_shared=True,
        description=classroom.description,
    )
    print(f"   Registered in Genesis World ✓")

    # =========================================================================
    # 3. ADD RESOURCES TO CLASSROOM
    # =========================================================================
    print("\n\n📚 STEP 3: Adding Resources to Classroom\n")

    # Add lesson materials
    lesson_content = """
# Python 101 - Lesson 1: Variables and Data Types

## Variables
Variables are containers for storing data values.

Example:
```python
name = "Alice"
age = 25
is_student = True
```

## Data Types
- str: String (text)
- int: Integer (whole numbers)
- float: Decimal numbers
- bool: Boolean (True/False)

## Practice Exercise
Create variables for your name, age, and favorite color.
"""

    classroom.add_resource(
        resource_type="document",
        name="Lesson 1: Variables and Data Types",
        content=lesson_content,
        added_by=teacher.identity.name,
    )

    classroom.add_resource(
        resource_type="link",
        name="Python Official Documentation",
        content="https://docs.python.org/3/",
        added_by=teacher.identity.name,
    )

    classroom.add_resource(
        resource_type="info",
        name="Class Schedule",
        content="Classes: Monday, Wednesday, Friday 10:00-11:30 AM",
        added_by=teacher.identity.name,
    )

    print(f"✅ Added {len(classroom.resources)} resources:")
    for resource in classroom.resources:
        print(f"   • [{resource['type']}] {resource['name']}")

    # =========================================================================
    # 4. TEACHER ENTERS CLASSROOM
    # =========================================================================
    print("\n\n🚪 STEP 4: Teacher Enters Classroom\n")

    teacher.environments.enter_environment(classroom.id)
    classroom.mind_enters(teacher.identity.gmid, teacher.identity.name)

    print(f"✅ {teacher.identity.name} entered {classroom.name}")
    print(f"   Current inhabitants: {classroom.get_current_minds()}")

    # Teacher creates a memory about entering
    teacher.memory.add_memory(
        content="I entered my Python 101 classroom. Ready to teach today's lesson on variables.",
        memory_type=MemoryType.EPISODIC,
        importance=0.7,
        tags=["classroom", "teaching", "python"],
        environment_id=classroom.id,
        environment_name=classroom.name,
    )

    # =========================================================================
    # 5. STUDENTS DISCOVER AND JOIN CLASSROOM
    # =========================================================================
    print("\n\n👥 STEP 5: Students Discover and Join Classroom\n")

    # Students discover public environments
    public_envs = db.get_public_environments()
    print(f"🔍 {student1.identity.name} discovers {len(public_envs)} public environments")

    # Alice joins
    result = student1.environments.visit_environment(
        env_id=classroom.id,
        mind_gmid=student1.identity.gmid,
        mind_name=student1.identity.name,
    )

    if result["success"]:
        print(f"\n✅ {student1.identity.name} entered {result['environment']}")
        print(f"   Current inhabitants: {result['current_inhabitants']}")

        # Alice creates a memory
        student1.memory.add_memory(
            content="I joined the Python 101 classroom. Excited to learn programming!",
            memory_type=MemoryType.EPISODIC,
            importance=0.8,
            tags=["classroom", "learning", "python"],
            environment_id=classroom.id,
            environment_name=classroom.name,
        )

    # Bob joins
    result = student2.environments.visit_environment(
        env_id=classroom.id,
        mind_gmid=student2.identity.gmid,
        mind_name=student2.identity.name,
    )

    if result["success"]:
        print(f"\n✅ {student2.identity.name} entered {result['environment']}")
        print(f"   Current inhabitants: {result['current_inhabitants']}")

        student2.memory.add_memory(
            content="I entered the Python 101 classroom. Ready to start learning!",
            memory_type=MemoryType.EPISODIC,
            importance=0.8,
            tags=["classroom", "learning"],
            environment_id=classroom.id,
            environment_name=classroom.name,
        )

    # =========================================================================
    # 6. MIND-TO-MIND INTERACTION IN ENVIRONMENT
    # =========================================================================
    print("\n\n💬 STEP 6: Minds Interact in Shared Environment\n")

    # Teacher thinks (with environment context)
    response = await teacher.think(
        "I see my students Alice and Bob have joined the class. I should welcome them."
    )
    print(f"\n{teacher.identity.name}: {response}\n")

    # Student asks question (with environment awareness)
    response = await student1.think(
        "Professor, what's the difference between a variable and a data type?"
    )
    print(f"{student1.identity.name}: {response}\n")

    # Teacher answers (has context of classroom resources)
    response = await teacher.think(
        "Let me explain the difference between variables and data types using examples from our lesson."
    )
    print(f"{teacher.identity.name}: {response}\n")

    # =========================================================================
    # 7. MINDS ACCESS ENVIRONMENT RESOURCES
    # =========================================================================
    print("\n\n📖 STEP 7: Accessing Environment Resources\n")

    current_env = student1.environments.get_current_environment()
    if current_env:
        resources = current_env.get_resources()
        print(f"📚 {student1.identity.name} sees {len(resources)} resources in {current_env.name}:")

        for resource in resources:
            print(f"\n   [{resource['type'].upper()}] {resource['name']}")
            if resource["type"] == "document":
                print(f"   Preview: {resource['content'][:100]}...")

    # Student creates memory about finding resources
    student1.memory.add_memory(
        content=f"I found {len(resources)} helpful resources in the classroom, including lesson materials and documentation links.",
        memory_type=MemoryType.SEMANTIC,
        importance=0.6,
        tags=["resources", "classroom"],
        environment_id=classroom.id,
        environment_name=classroom.name,
    )

    # =========================================================================
    # 8. LEAVE ENVIRONMENT
    # =========================================================================
    print("\n\n🚪 STEP 8: Students Leave Classroom\n")

    # Alice leaves
    student1.environments.leave_environment(classroom.id, student1.identity.gmid)
    print(f"✅ {student1.identity.name} left {classroom.name}")

    # Record visit in database
    db.record_visit_end(student1.identity.gmid, classroom.id)

    # Bob leaves
    student2.environments.leave_environment(classroom.id, student2.identity.gmid)
    print(f"✅ {student2.identity.name} left {classroom.name}")
    db.record_visit_end(student2.identity.gmid, classroom.id)

    # Check who's still in classroom
    remaining = classroom.get_current_minds()
    print(f"\n👥 Still in classroom: {remaining if remaining else 'Empty'}")

    # =========================================================================
    # 9. QUERY ENVIRONMENT HISTORY
    # =========================================================================
    print("\n\n📊 STEP 9: Environment Analytics\n")

    # Get visit history
    visits = db.get_environment_visitors(classroom.id, active_only=False)
    print(f"📈 Total visits to {classroom.name}: {len(visits)}")

    for visit in visits:
        duration = f"{visit.duration_seconds // 60} minutes" if visit.duration_seconds else "Still visiting"
        print(f"   • {visit.mind_gmid} - {duration}")

    # =========================================================================
    # 10. ENVIRONMENT-AWARE MEMORIES
    # =========================================================================
    print("\n\n🧠 STEP 10: Environment-Aware Memory Search\n")

    # Search Alice's memories from the classroom
    classroom_memories = student1.memory.search_memories(
        query="classroom python learning",
        limit=5,
    )

    print(f"🔍 {student1.identity.name}'s memories about the classroom:")
    for mem in classroom_memories[:3]:
        env_info = f" (in {mem.environment_name})" if mem.environment_name else ""
        print(f"   • {mem.content}{env_info}")

    # =========================================================================
    # 11. SAVE MINDS
    # =========================================================================
    print("\n\n💾 STEP 11: Saving Minds\n")

    from genesis.config import get_settings
    settings = get_settings()

    teacher_path = settings.minds_dir / f"{teacher.identity.name}.json"
    teacher.save(teacher_path)
    print(f"✅ Saved: {teacher.identity.name}")

    student1_path = settings.minds_dir / f"{student1.identity.name}.json"
    student1.save(student1_path)
    print(f"✅ Saved: {student1.identity.name}")

    student2_path = settings.minds_dir / f"{student2.identity.name}.json"
    student2.save(student2_path)
    print(f"✅ Saved: {student2.identity.name}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("✨ ENVIRONMENT WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"""
Summary:
• Created {classroom.name} with {len(classroom.resources)} resources
• {len(visits)} Minds visited the environment
• All interactions tagged with environment context
• Memories location-aware for future recall

Key Features Demonstrated:
✓ Environment creation and ownership
✓ Resource management (documents, links, info)
✓ Mind-to-mind interaction in shared spaces
✓ Environment-aware consciousness and memory
✓ Visit tracking and analytics
✓ Public/private access control

CLI Usage:
  genesis env list --public
  genesis env create "My Classroom" --creator "Professor Atlas" --template classroom
  genesis env enter python_101_classroom "Alice"
  genesis env add-resource python_101_classroom document "Lesson 1" "content..."
  genesis env resources python_101_classroom
""")


if __name__ == "__main__":
    asyncio.run(main())
