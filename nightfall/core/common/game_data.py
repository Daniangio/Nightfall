from nightfall.core.common.enums import BuildingType, CityTerrainType, UnitType
from nightfall.core.common.datatypes import Resources

# Central repository for game balance numbers. Production values are per hour.
BUILDING_DATA = {
    BuildingType.CITADEL: {
        'production': { # Base resource flow
            1: Resources(food=5, wood=5, iron=2),
            2: Resources(food=7, wood=7, iron=3),
            3: Resources(food=10, wood=10, iron=5),
        },
        'provides': { # Stats provided by the Citadel at each level
            1: {'max_buildings': 100, 'storage': Resources(1000, 1000, 500)},
            2: {'max_buildings': 150, 'storage': Resources(2000, 2000, 1000)},
            3: {'max_buildings': 200, 'storage': Resources(4000, 4000, 2000)},
        },
        'upgrade': {
            # Level 1 is the starting level, so we define the cost to get to level 2
            2: {'cost': Resources(food=100, wood=100, iron=50), 'time': 10},
            3: {'cost': Resources(food=250, wood=250, iron=120), 'time': 10},
        },
    },
    BuildingType.FARM: {
        'build': {
            'time': 5, # Time in seconds
            'cost': Resources(food=0, wood=50, iron=10),
        },
        'upgrade': {
            2: {'cost': Resources(food=0, wood=130, iron=40), 'time': 10},
            3: {'cost': Resources(food=0, wood=180, iron=55), 'time': 10},
            4: {'cost': Resources(food=0, wood=230, iron=70), 'time': 10},
            5: {'cost': Resources(food=0, wood=280, iron=85), 'time': 10},
            6: {'cost': Resources(food=0, wood=330, iron=100), 'time': 10},
            7: {'cost': Resources(food=0, wood=380, iron=115), 'time': 10},
            8: {'cost': Resources(food=0, wood=430, iron=130), 'time': 10},
            9: {'cost': Resources(food=0, wood=480, iron=145), 'time': 10},
            10: {'cost': Resources(food=0, wood=530, iron=160), 'time': 10},
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
            BuildingType.BUILDERS_HUT.name: 0.10, # +10% production for each adjacent Builder's Hut
        }
    },
    BuildingType.LUMBER_MILL: {
        'build': {
            'cost': Resources(food=0, wood=30, iron=20),
            'time': 35,
        },
        'upgrade': {
            2: {'cost': Resources(food=0, wood=90, iron=50), 'time': 10},
            3: {'cost': Resources(food=0, wood=120, iron=65), 'time': 10},
            4: {'cost': Resources(food=0, wood=150, iron=80), 'time': 10},
            5: {'cost': Resources(food=0, wood=180, iron=95), 'time': 10},
            6: {'cost': Resources(food=0, wood=210, iron=110), 'time': 10},
            7: {'cost': Resources(food=0, wood=240, iron=125), 'time': 10},
            8: {'cost': Resources(food=0, wood=270, iron=140), 'time': 10},
            9: {'cost': Resources(food=0, wood=300, iron=155), 'time': 10},
            10: {'cost': Resources(food=0, wood=330, iron=170), 'time': 10},
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
            BuildingType.BUILDERS_HUT.name: 0.10, # +10% production for each adjacent Builder's Hut
        }
    },
    BuildingType.IRON_MINE: {
        'build': {
            'cost': Resources(food=0, wood=60, iron=30),
            'time': 40,
        },
        'upgrade': {
            2: {'cost': Resources(food=0, wood=150, iron=75), 'time': 10},
            3: {'cost': Resources(food=0, wood=200, iron=100), 'time': 10},
            4: {'cost': Resources(food=0, wood=250, iron=125), 'time': 10},
            5: {'cost': Resources(food=0, wood=300, iron=150), 'time': 10},
            6: {'cost': Resources(food=0, wood=350, iron=175), 'time': 10},
            7: {'cost': Resources(food=0, wood=400, iron=200), 'time': 10},
            8: {'cost': Resources(food=0, wood=450, iron=225), 'time': 10},
            9: {'cost': Resources(food=0, wood=500, iron=250), 'time': 10},
            10: {'cost': Resources(food=0, wood=550, iron=275), 'time': 10},
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
            BuildingType.BUILDERS_HUT.name: 0.10, # +10% production for each adjacent Builder's Hut
        }
    },
    BuildingType.BARRACKS: {
        'build': {
            'cost': Resources(food=50, wood=100, iron=80),
            'time': 60,
        },
        'upgrade': {
            2: {'cost': Resources(food=0, wood=150, iron=120), 'time': 10},
            3: {'cost': Resources(food=0, wood=250, iron=200), 'time': 10},
        },
        # Additive bonus to recruitment speed. 0.1 = +10% speed.
        'recruitment_speed_bonus': {
            1: 0.10,
            2: 0.15,
            3: 0.20,
        }
    }
,
    BuildingType.WAREHOUSE: {
        'build': {
            'cost': Resources(food=100, wood=250, iron=50),
            'time': 5,
        },
        'upgrade': {
            2: {'cost': Resources(food=0, wood=300, iron=100), 'time': 60},
            3: {'cost': Resources(food=0, wood=400, iron=150), 'time': 90},
        },
        'provides': { # Base storage provided by the warehouse at each level
            1: {'storage': Resources(500, 500, 250)},
            2: {'storage': Resources(1000, 1000, 500)},
            3: {'storage': Resources(2000, 2000, 1000)},
        },
        'adjacency_bonus': {
            CityTerrainType.FOREST_PLOT.name: 0.10, # +10% storage for each adjacent Forest Plot
        }
    },
    BuildingType.BUILDERS_HUT: {
        'build': {
            'cost': Resources(food=100, wood=150, iron=200),
            'time': 5,
        },
        'upgrade': {
            2: {'cost': Resources(food=0, wood=200, iron=250), 'time': 75},
            3: {'cost': Resources(food=0, wood=300, iron=350), 'time': 120},
        },
        'provides': { # Additive bonus to construction speed. 0.05 = +5% speed.
            1: {'construction_speed_bonus': 1.00},
            2: {'construction_speed_bonus': 1.10},
            3: {'construction_speed_bonus': 1.15},
        }
    }
}

# Data for recruitable units
UNIT_DATA = {
    UnitType.SWORDSMAN: {
        'cost': Resources(food=20, wood=5, iron=10),
        'base_recruit_time': 10, # in seconds per unit
    }
}

# Cost to demolish any building or clear a resource plot
DEMOLISH_COST_BUILDING = {'cost': Resources(food=10, wood=10, iron=0), 'time': 15}
DEMOLISH_COST_RESOURCE = {'cost': Resources(food=40, wood=40, iron=0), 'time': 20}
