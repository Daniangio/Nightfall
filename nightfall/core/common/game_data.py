from nightfall.core.common.enums import BuildingType, CityTerrainType, UnitType
from nightfall.core.common.datatypes import Resources

# Central repository for game balance numbers
BUILDING_DATA = {
    BuildingType.CITADEL: {
        'action_point_cost': 2, # Upgrading the Citadel is expensive
        'production': { # Base resource flow
            1: Resources(food=5, wood=5, iron=2),
            2: Resources(food=7, wood=7, iron=3),
            3: Resources(food=10, wood=10, iron=5),
        },
        'provides': { # Stats provided by the Citadel at each level
            1: {'max_buildings': 10, 'action_points': 3},
            2: {'max_buildings': 15, 'action_points': 4},
            3: {'max_buildings': 20, 'action_points': 5},
        },
        'upgrade': {
            # Level 1 is the starting level, so we define the cost to get to level 2
            2: {'cost': Resources(food=100, wood=100, iron=50)},
            3: {'cost': Resources(food=250, wood=250, iron=120)},
        },
    },
    BuildingType.FARM: {
        'action_point_cost': 1,
        'build': {
            'cost': Resources(food=0, wood=50, iron=10),
        },
        'upgrade': {
            2: {'cost': Resources(food=0, wood=130, iron=40)},
            3: {'cost': Resources(food=0, wood=180, iron=55)},
            4: {'cost': Resources(food=0, wood=230, iron=70)},
            5: {'cost': Resources(food=0, wood=280, iron=85)},
            6: {'cost': Resources(food=0, wood=330, iron=100)},
            7: {'cost': Resources(food=0, wood=380, iron=115)},
            8: {'cost': Resources(food=0, wood=430, iron=130)},
            9: {'cost': Resources(food=0, wood=480, iron=145)},
            10: {'cost': Resources(food=0, wood=530, iron=160)},
        },
        'production': {
            1: Resources(food=5, wood=0, iron=0),
            2: Resources(food=10, wood=0, iron=0),
            3: Resources(food=16, wood=0, iron=0),
            4: Resources(food=22, wood=0, iron=0),
            5: Resources(food=28, wood=0, iron=0),
            6: Resources(food=34, wood=0, iron=0),
            7: Resources(food=40, wood=0, iron=0),
            8: Resources(food=46, wood=0, iron=0),
            9: Resources(food=52, wood=0, iron=0),
            10: Resources(food=58, wood=0, iron=0),
        },
        'adjacency_bonus': {
            CityTerrainType.WATER.name: 0.25, # +25% production for each adjacent Water tile
            CityTerrainType.GRASS.name: 0.05, # +5% production for each adjacent Grass tile
        }
    },
    BuildingType.LUMBER_MILL: {
        'action_point_cost': 1,
        'build': {
            'cost': Resources(food=0, wood=30, iron=20),
        },
        'upgrade': {
            2: {'cost': Resources(food=0, wood=90, iron=50)},
            3: {'cost': Resources(food=0, wood=120, iron=65)},
            4: {'cost': Resources(food=0, wood=150, iron=80)},
            5: {'cost': Resources(food=0, wood=180, iron=95)},
            6: {'cost': Resources(food=0, wood=210, iron=110)},
            7: {'cost': Resources(food=0, wood=240, iron=125)},
            8: {'cost': Resources(food=0, wood=270, iron=140)},
            9: {'cost': Resources(food=0, wood=300, iron=155)},
            10: {'cost': Resources(food=0, wood=330, iron=170)},
        },
        'production': {
            1: Resources(food=0, wood=5, iron=0),
            2: Resources(food=0, wood=10, iron=0),
            3: Resources(food=0, wood=15, iron=0),
            4: Resources(food=0, wood=20, iron=0),
            5: Resources(food=0, wood=25, iron=0),
            6: Resources(food=0, wood=30, iron=0),
            7: Resources(food=0, wood=35, iron=0),
            8: Resources(food=0, wood=40, iron=0),
            9: Resources(food=0, wood=45, iron=0),
            10: Resources(food=0, wood=50, iron=0),
        },
        'adjacency_bonus': {
            CityTerrainType.FOREST_PLOT.name: 0.20, # +20% production for each adjacent Forest Plot
        }
    },
    BuildingType.IRON_MINE: {
        'action_point_cost': 1,
        'build': {
            'cost': Resources(food=0, wood=60, iron=30),
        },
        'upgrade': {
            2: {'cost': Resources(food=0, wood=150, iron=75)},
            3: {'cost': Resources(food=0, wood=200, iron=100)},
            4: {'cost': Resources(food=0, wood=250, iron=125)},
            5: {'cost': Resources(food=0, wood=300, iron=150)},
            6: {'cost': Resources(food=0, wood=350, iron=175)},
            7: {'cost': Resources(food=0, wood=400, iron=200)},
            8: {'cost': Resources(food=0, wood=450, iron=225)},
            9: {'cost': Resources(food=0, wood=500, iron=250)},
            10: {'cost': Resources(food=0, wood=550, iron=275)},
        },
        'production': {
            1: Resources(food=0, wood=0, iron=5),
            2: Resources(food=0, wood=0, iron=10),
            3: Resources(food=0, wood=0, iron=15),
            4: Resources(food=0, wood=0, iron=20),
            5: Resources(food=0, wood=0, iron=25),
            6: Resources(food=0, wood=0, iron=30),
            7: Resources(food=0, wood=0, iron=35),
            8: Resources(food=0, wood=0, iron=40),
            9: Resources(food=0, wood=0, iron=45),
            10: Resources(food=0, wood=0, iron=50),
        },
        'adjacency_bonus': {
            CityTerrainType.IRON_DEPOSIT.name: 0.20, # +20% production for each adjacent Iron Deposit
        }
    },
    BuildingType.BARRACKS: {
        'action_point_cost': 1,
        'build': {
            'cost': Resources(food=50, wood=100, iron=80),
        },
        'upgrade': {
            2: {'cost': Resources(food=0, wood=150, iron=120)},
            3: {'cost': Resources(food=0, wood=250, iron=200)},
        },
        # Additive bonus to recruitment speed. 0.1 = +10% speed.
        'recruitment_speed_bonus': {
            1: 0.10,
            2: 0.15,
            3: 0.20,
        }
    }
}

# Data for recruitable units
UNIT_DATA = {
    UnitType.SWORDSMAN: {
        'cost': Resources(food=20, wood=5, iron=10),
        'base_recruit_time': 1.0, # in turns (days) per unit
        'action_point_cost': 1, # AP cost to start a batch of recruitment
    }
}

# Cost to demolish any building or clear a resource plot
DEMOLISH_COST_BUILDING = {'cost': Resources(food=10, wood=10, iron=0), 'action_point_cost': 1}
DEMOLISH_COST_RESOURCE = {'cost': Resources(food=40, wood=40, iron=0), 'action_point_cost': 1}
