import asyncio
from state import StudentState, DialogueRole, EmotionType
from agents import SocraticEvaluatorAgent

async def test():
    agent = SocraticEvaluatorAgent()

    state = StudentState(student_id="test_s", course_id="bigdata")
    state.add_message(DialogueRole.STUDENT, "我不懂HDFS是什么")
    state.metadata["dialogue_type"] = "confusion"

    state = await agent.run(state)
    resp = state.metadata.get("socratic_response", "")
    print(f"Round 1 response: {resp[:100]}...")
    print(f"  interaction_count={state.profile.interaction_count}, pass_rate={state.profile.socratic_pass_rate}")

    state2 = StudentState(student_id="test_s2", course_id="bigdata")
    state2.add_message(DialogueRole.STUDENT, "讲一下Spark")
    state2.metadata["dialogue_type"] = "question"

    state2 = await agent.run(state2)
    print(f"Non-confusion: interaction_count={state2.profile.interaction_count}")
    print(f"  evaluation={state2.metadata.get('evaluation', {})}")

    data = agent._get_topic_fallback_data("HDFS分布式文件系统")
    print(f"Fallback data keys: {list(data.keys())}")
    print(f"  Has mermaid: {'mermaid' in data}")

    print()
    print("SocraticEvaluatorAgent test PASSED")

asyncio.run(test())
