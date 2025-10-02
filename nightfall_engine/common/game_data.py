from nightfall_engine.common.enums import BuildingType, CityTerrainType
from nightfall_engine.common.datatypes import Resources

# Central repository for game balance numbers
BUILDING_DATA = {
    BuildingType.CITADEL: {}, # No cost, cannot be built
    BuildingType.FARM: {
        'build': {'cost': Resources(food=0, wood=50, iron=10)},
        'upgrade': {
            1: {'cost': Resources(food=0, wood=80, iron=25)},
            2: {'cost': Resources(food=0, wood=130, iron=40)},
        },
        'production': {
            1: Resources(food=5, wood=0, iron=0),
            2: Resources(food=10, wood=0, iron=0),
            3: Resources(food=16, wood=0, iron=0),
        },
        'adjacency_bonus': {
            CityTerrainType.WATER.name: 0.25, # +25% production for each adjacent Water tile
            CityTerrainType.GRASS.name: 0.05, # +5% production for each adjacent Grass tile
        }
    },
    BuildingType.LUMBER_MILL: {
        'build': {'cost': Resources(food=0, wood=30, iron=20)},
        'upgrade': {
            1: {'cost': Resources(food=0, wood=60, iron=35)},
        },
        'production': {
            1: Resources(food=0, wood=5, iron=0),
            2: Resources(food=0, wood=10, iron=0),
        },
        'adjacency_bonus': {
            CityTerrainType.FOREST_PLOT.name: 0.20, # +20% production for each adjacent Forest Plot
        }
    },
    BuildingType.IRON_MINE: {
        'build': {'cost': Resources(food=0, wood=60, iron=30)},
        'upgrade': {
            1: {'cost': Resources(food=0, wood=100, iron=50)},
        },
        'production': {
            1: Resources(food=0, wood=0, iron=5),
            2: Resources(food=0, wood=0, iron=10),
        },
        'adjacency_bonus': {
            CityTerrainType.IRON_DEPOSIT.name: 0.20, # +20% production for each adjacent Iron Deposit
        }
    }
}

# Cost to demolish any building or clear a resource plot
DEMOLISH_COST = Resources(food=10, wood=10, iron=0)
