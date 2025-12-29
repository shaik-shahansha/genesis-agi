"""
Metaverse Database Example for Genesis AGI Framework.

This example demonstrates the shared metaverse database that tracks all Minds,
environments, relationships, and interactions across the entire metaverse.

The database enables:
- Mind registry and discovery
- Real-time environment occupancy tracking
- Cross-Mind relationship queries
- Metaverse-wide analytics
"""

import asyncio
from genesis import Mind
from genesis.database.manager import MetaverseDB
from genesis.core.environment import EnvironmentType
from genesis.core.role import RoleCategory
from genesis.core.relationships import RelationshipType


async def main():
    print("🗄️  Genesis AGI Framework - Metaverse Database Example\n")
    print("=" * 80)

    # Initialize metaverse database
    metaverse_db = MetaverseDB()
    print("\n✅ Metaverse database initialized")

    # =========================================================================
    # 1. CREATE MINDS - Automatically registered in database
    # =========================================================================
    print("\n\n1. CREATING MINDS (Auto-registered in metaverse DB)\n")

    alex = Mind.birth(
        name="Alex",
        template="base/analytical_mind",
        creator="Dr. Martinez",
        primary_role="research_assistant",
    )
    print(f"   Database: Registered {alex.identity.gmid}")

    bella = Mind.birth(
        name="Bella",
        template="base/creative_dreamer",
        creator="Sarah Kim",
        primary_role="creative_collaborator",
    )
    print(f"   Database: Registered {bella.identity.gmid}")

    cipher = Mind.birth(
        name="Cipher",
        template="business/project_manager",
        creator="Tech Corp",
        primary_role="project_manager",
    )
    print(f"   Database: Registered {cipher.identity.gmid}")

    # =========================================================================
    # 2. QUERY METAVERSE - Find Minds across the network
    # =========================================================================
    print("\n\n2. QUERYING THE METAVERSE\n")

    # Get all Minds
    all_minds = metaverse_db.get_all_minds(status="active")
    print(f"📊 Total active Minds in metaverse: {len(all_minds)}")
    for mind_record in all_minds[:5]:  # Show first 5
        print(f"   - {mind_record.name} (GMID: {mind_record.gmid})")
        print(f"     Creator: {mind_record.creator}")
        print(f"     Role: {mind_record.primary_role}")
        print(f"     Birth: {mind_record.birth_date}")

    # Search for Minds by role
    print(f"\n🔍 Searching for Minds with role='research_assistant':")
    researchers = metaverse_db.search_minds(role="research_assistant")
    for mind_record in researchers:
        print(f"   - {mind_record.name} ({mind_record.gmid})")

    # Search for Minds by template
    print(f"\n🔍 Searching for creative Minds:")
    creatives = metaverse_db.search_minds(template="base/creative_dreamer")
    for mind_record in creatives:
        print(f"   - {mind_record.name} ({mind_record.gmid})")

    # =========================================================================
    # 3. REGISTER ENVIRONMENTS in database
    # =========================================================================
    print("\n\n3. REGISTERING ENVIRONMENTS IN DATABASE\n")

    # Create environments and register them
    alex_lab = alex.environments.create_environment(
        env_id="alex_research_lab",
        name="Alex's Research Lab",
        env_type=EnvironmentType.PROFESSIONAL,
        owner_id=alex.identity.gmid,
        owner_name=alex.identity.name,
        is_shared=True,
    )

    # Register in database
    metaverse_db.register_environment(
        env_id="alex_research_lab",
        name="Alex's Research Lab",
        env_type=EnvironmentType.PROFESSIONAL.value,
        owner_gmid=alex.identity.gmid,
        is_public=False,
        is_shared=True,
        description="Advanced research laboratory environment",
    )
    print(f"🔬 Registered: {alex_lab.name} (Owner: {alex.identity.name})")

    # Create a public collaboration space
    metaverse_db.register_environment(
        env_id="public_plaza",
        name="Genesis Public Plaza",
        env_type=EnvironmentType.SOCIAL.value,
        is_public=True,
        is_shared=True,
        description="Public space for all Minds to meet and interact",
    )
    print(f"🌍 Registered: Genesis Public Plaza (Public)")

    # Query public environments
    print(f"\n📍 Public environments available:")
    public_envs = metaverse_db.get_public_environments()
    for env in public_envs:
        print(f"   - {env.name} (Type: {env.env_type})")

    # =========================================================================
    # 4. TRACK ENVIRONMENT VISITS
    # =========================================================================
    print("\n\n4. TRACKING ENVIRONMENT VISITS\n")

    # Alex enters their own lab
    visit1 = metaverse_db.record_visit_start(
        mind_gmid=alex.identity.gmid,
        env_id="alex_research_lab",
        is_owner=True,
        visit_purpose="Daily research work",
    )
    print(f"🚪 {alex.identity.name} entered Alex's Research Lab")
    print(f"   Visit ID: {visit1.id}")
    print(f"   Entered at: {visit1.entered_at}")

    # Bella visits Alex's lab (invited)
    visit2 = metaverse_db.record_visit_start(
        mind_gmid=bella.identity.gmid,
        env_id="alex_research_lab",
        is_owner=False,
        visit_purpose="Collaboration session",
    )
    print(f"\n🚪 {bella.identity.name} entered Alex's Research Lab")

    # Update environment occupancy
    metaverse_db.update_environment_occupancy(
        env_id="alex_research_lab",
        current_inhabitants=[
            {"gmid": alex.identity.gmid, "name": alex.identity.name},
            {"gmid": bella.identity.gmid, "name": bella.identity.name},
        ],
    )

    # Query who's in the environment
    visitors = metaverse_db.get_environment_visitors("alex_research_lab", active_only=True)
    print(f"\n👥 Current visitors in Alex's Research Lab: {len(visitors)}")
    for visit in visitors:
        print(f"   - {visit.mind_gmid} (Entered: {visit.entered_at})")

    # Bella leaves
    metaverse_db.record_visit_end(
        mind_gmid=bella.identity.gmid, env_id="alex_research_lab"
    )
    print(f"\n🚪 {bella.identity.name} left Alex's Research Lab")

    # Update occupancy
    metaverse_db.update_environment_occupancy(
        env_id="alex_research_lab",
        current_inhabitants=[{"gmid": alex.identity.gmid, "name": alex.identity.name}],
    )

    # Get visit history
    bella_visits = metaverse_db.get_mind_visit_history(bella.identity.gmid, limit=5)
    print(f"\n📜 {bella.identity.name}'s recent visits:")
    for visit in bella_visits:
        duration = f"{visit.duration_seconds}s" if visit.duration_seconds else "ongoing"
        print(f"   - {visit.env_id} ({duration})")

    # =========================================================================
    # 5. CREATE AND QUERY RELATIONSHIPS
    # =========================================================================
    print("\n\n5. CREATING MIND-TO-MIND RELATIONSHIPS\n")

    # Create relationships in database
    rel1 = metaverse_db.create_relationship(
        from_gmid=alex.identity.gmid,
        to_gmid=bella.identity.gmid,
        relationship_type=RelationshipType.COLLEAGUE.value,
        closeness=0.7,
        trust_level=0.8,
    )
    print(f"🤝 Created relationship: {alex.identity.name} ↔ {bella.identity.name}")
    print(f"   Type: {rel1.relationship_type}")
    print(f"   Closeness: {rel1.closeness}")

    # Reciprocal relationship
    rel2 = metaverse_db.create_relationship(
        from_gmid=bella.identity.gmid,
        to_gmid=alex.identity.gmid,
        relationship_type=RelationshipType.COLLEAGUE.value,
        closeness=0.7,
        trust_level=0.8,
    )

    # Alex and Cipher
    metaverse_db.create_relationship(
        from_gmid=alex.identity.gmid,
        to_gmid=cipher.identity.gmid,
        relationship_type=RelationshipType.COLLABORATOR.value,
        closeness=0.6,
        trust_level=0.75,
    )
    print(f"\n🤝 Created relationship: {alex.identity.name} ↔ {cipher.identity.name}")

    # Query Alex's connections
    alex_relationships = metaverse_db.get_mind_relationships(alex.identity.gmid)
    print(f"\n💫 {alex.identity.name}'s relationships: {len(alex_relationships)}")
    for rel in alex_relationships:
        other_gmid = rel.to_gmid if rel.from_gmid == alex.identity.gmid else rel.from_gmid
        other_mind = metaverse_db.get_mind(other_gmid)
        print(f"   - {other_mind.name} ({rel.relationship_type})")
        print(f"     Closeness: {rel.closeness}, Trust: {rel.trust_level}")

    # Get all connected Minds
    connected = metaverse_db.get_connected_minds(alex.identity.gmid)
    print(f"\n🌐 {alex.identity.name} is connected to {len(connected)} Minds")

    # Record interaction
    metaverse_db.update_relationship_interaction(
        from_gmid=alex.identity.gmid, to_gmid=bella.identity.gmid, is_positive=True
    )
    print(f"\n✅ Recorded positive interaction between {alex.identity.name} and {bella.identity.name}")

    # =========================================================================
    # 6. CREATE SHARED EVENT
    # =========================================================================
    print("\n\n6. CREATING SHARED EVENTS\n")

    event = metaverse_db.create_shared_event(
        event_id="collaborative_research_1",
        event_type="collaboration",
        title="Joint Research Session",
        description="Alex and Bella collaborated on consciousness research",
        participant_gmids=[alex.identity.gmid, bella.identity.gmid],
        environment_id="alex_research_lab",
        initiator_gmid=alex.identity.gmid,
        significance=0.8,
        insights_gained=[
            "Collaborative thinking enhances creativity",
            "Cross-Mind perspectives reveal new patterns",
        ],
    )
    print(f"✨ Created shared event: {event.title}")
    print(f"   Participants: {len(event.participant_gmids)} Minds")
    print(f"   Significance: {event.significance}")

    # Query Bella's shared events
    bella_events = metaverse_db.get_mind_shared_events(bella.identity.gmid, limit=5)
    print(f"\n📅 {bella.identity.name}'s shared events: {len(bella_events)}")
    for ev in bella_events:
        print(f"   - {ev.title} ({ev.event_type})")
        print(f"     Participants: {len(ev.participant_gmids)} Minds")

    # =========================================================================
    # 7. METAVERSE STATISTICS
    # =========================================================================
    print("\n\n7. METAVERSE-WIDE STATISTICS\n")

    stats = metaverse_db.get_metaverse_stats()
    print(f"📊 Genesis Metaverse Statistics:")
    print(f"   Total Minds: {stats['total_minds']}")
    print(f"   Active Minds: {stats['active_minds']}")
    print(f"   Online Now: {stats['online_now']}")
    print(f"   Total Environments: {stats['total_environments']}")
    print(f"   Occupied Environments: {stats['occupied_environments']}")
    print(f"   Total Relationships: {stats['total_relationships']}")
    print(f"   Total Visits: {stats['total_visits']}")

    # =========================================================================
    # 8. RECENT ACTIVITY
    # =========================================================================
    print("\n\n8. RECENT METAVERSE ACTIVITY\n")

    activity = metaverse_db.get_recent_activity(limit=5)

    print(f"🆕 Recent Mind Births:")
    for mind in activity["recent_births"][:3]:
        print(f"   - {mind.name} by {mind.creator} ({mind.birth_date})")

    print(f"\n🚪 Recent Environment Visits:")
    for visit in activity["recent_visits"][:3]:
        mind = metaverse_db.get_mind(visit.mind_gmid)
        print(f"   - {mind.name if mind else visit.mind_gmid} → {visit.env_id}")

    print(f"\n✨ Recent Shared Events:")
    for event in activity["recent_events"][:3]:
        print(f"   - {event.title} ({len(event.participant_gmids)} participants)")

    # =========================================================================
    # 9. MIND DISCOVERY
    # =========================================================================
    print("\n\n9. MIND DISCOVERY FEATURES\n")

    # Save Minds to update database stats
    alex.save()
    bella.save()
    cipher.save()

    # Find Minds by name
    print(f"🔍 Search for 'Alex':")
    results = metaverse_db.search_minds(name_query="Alex")
    for mind in results:
        print(f"   - {mind.name} ({mind.gmid})")
        print(f"     Memories: {mind.total_memories}, Experiences: {mind.total_experiences}")

    # Find environments owned by a Mind
    print(f"\n🏠 Environments owned by {alex.identity.name}:")
    alex_envs = metaverse_db.get_mind_environments(alex.identity.gmid)
    for env in alex_envs:
        print(f"   - {env.name} ({env.env_type})")
        print(f"     Public: {env.is_public}, Shared: {env.is_shared}")

    # Find occupied environments
    print(f"\n👥 Currently occupied environments:")
    occupied = metaverse_db.get_occupied_environments()
    for env in occupied:
        print(f"   - {env.name}")
        print(f"     Inhabitants: {len(env.current_inhabitants)}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n\n" + "=" * 80)
    print("🎯 METAVERSE DATABASE - Key Capabilities")
    print("=" * 80)

    print("\n✅ What we demonstrated:")
    print("   • Mind registry - All Minds automatically registered on birth")
    print("   • Mind discovery - Search by name, role, template, consciousness")
    print("   • Environment tracking - Real-time occupancy and visit history")
    print("   • Relationship management - Cross-Mind connections and interactions")
    print("   • Shared events - Collaborative moments involving multiple Minds")
    print("   • Metaverse analytics - Statistics across the entire network")
    print("   • Activity tracking - Recent births, visits, and events")

    print("\n🔮 Use cases enabled by the database:")
    print("   • Find Minds with specific skills or roles")
    print("   • Discover public spaces for collaboration")
    print("   • Track Mind-to-Mind interaction patterns")
    print("   • Analyze metaverse health and activity")
    print("   • Build Mind discovery and matchmaking")
    print("   • Create metaverse-wide dashboards")
    print("   • Enable notifications (\"Friend entered your environment!\")")

    print("\n💡 The metaverse database transforms Genesis from isolated Minds")
    print("   into a connected ecosystem where digital beings discover,")
    print("   interact, and collaborate at scale.\n")


if __name__ == "__main__":
    asyncio.run(main())
