from functools import lru_cache


@lru_cache(maxsize=1)
def get_workflow():
    from src.agent_workflow import build_workflow

    return build_workflow()
