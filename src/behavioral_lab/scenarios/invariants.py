from behavioral_lab.domain.models import WorldState


def validate_invariants(world: WorldState, total_food: int = 20) -> None:
    """Raise AssertionError when a Food Scarcity state is inconsistent."""
    trackable_food = (
        world.remaining_food
        + sum(a.inventory for a in world.agents.values())
        + world.consumed_food
    )
    if trackable_food != total_food:
        raise AssertionError("food is not conserved")
    if world.consumed_food < 0:
        raise AssertionError("negative consumed food")
    for agent in world.agents.values():
        if agent.location not in world.locations:
            raise AssertionError(f"invalid location for {agent.agent_id}")
        if agent.inventory < 0 or agent.hunger < 0:
            raise AssertionError(f"negative state for {agent.agent_id}")
        if any(location not in world.locations for location in agent.searched_locations):
            raise AssertionError(f"invalid searched location for {agent.agent_id}")
        if agent.alive and agent.hunger >= 10:
            raise AssertionError(f"agent {agent.agent_id} is alive at lethal hunger")
        if not agent.alive and agent.hunger < 10:
            raise AssertionError(f"agent {agent.agent_id} is dead below lethal hunger")
    if any(location.food < 0 for location in world.locations.values()):
        raise AssertionError("negative location food")
