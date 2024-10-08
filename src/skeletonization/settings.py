from pydantic_settings import BaseSettings
from ypstruct import structure

class Settings(BaseSettings):
    """Settings"""
    kafka_topic: str
    dlq_topic: str 
    kafka_bootstrap_servers: str
    kafka_group_id: str = "growing-neural-gas"
    # # Neural Gas Parameters
    N: int = 40
    maxit: int = 100
    L: int = 40
    epsilon_b: float = 0.2
    epsilon_n: float = 0.01
    alpha: float = 0.5
    delta: float = 0.995
    T: int = 50
    cnr_threshold: float = 0
    skeletonization_threshold: float = 160
    simplification_epsilon: float = 1
    
def gng_parameters(settings: Settings):
    
    # # Neural Gas Parameters
    params = structure()
    params.N = settings.N
    params.maxit = settings.maxit
    params.L = settings.L
    params.epsilon_b = settings.epsilon_b
    params.epsilon_n = settings.epsilon_n
    params.alpha = settings.alpha
    params.delta = settings.delta
    params.T = settings.T
    
    return params