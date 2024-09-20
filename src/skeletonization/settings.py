from pydantic_settings import BaseSettings
from ypstruct import structure

class Settings(BaseSettings):
    """Settings"""
    kafka_topic: str
    dlq_topic: str 
    kafka_bootstrap_servers: str
    kafka_group_id: str = "growing-neural-gas"
    # # Neural Gas Parameters
    N = 40
    maxit = 50
    L = 40
    epsilon_b = 0.2
    epsilon_n = 0.01
    alpha = 0.5
    delta = 0.995
    T = 50
    cnr_threshold = 0
    
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
    params.T = settingsT
    
    return params