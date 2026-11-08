"""Select first admissible ranked action or an explicit wait boundary."""
def select(ranked):
    return ranked[0]['action'] if ranked else {'mode':'wait','explanation':'No admissible unattempted model-proposed action'}
