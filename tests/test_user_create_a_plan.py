from domain.entities.flow_validator import Plan


def test_user_can_create_an_plan():
    plan = Plan(id=1, name="Purchase flow")

    assert plan.name == "Purchase flow"
    assert plan.active is True
