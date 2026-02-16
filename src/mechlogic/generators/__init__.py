"""Part generators for mechanical logic compiler."""

from .lower_housing import LowerHousingGenerator
from .upper_housing import UpperHousingGenerator
from .shift_lever import ShiftLeverGenerator
from .axle import AxleGenerator
from .dog_clutch import DogClutchGenerator
from .gear_spur import SpurGearGenerator
from .gear_bevel import BevelGearGenerator

from .serpentine_flexure import SerpentineFlexureGenerator

# Assembly generators
from .bevel_pair import BevelPairGenerator
from .bevel_lever import BevelLeverGenerator
from .bevel_lever_with_upper_housing import BevelLeverWithUpperHousingGenerator
from .selector_mechanism import SelectorMechanismGenerator
from .selector_with_housing import SelectorWithHousingGenerator
from .combined_selector import CombinedSelectorGenerator
from .mux_selector import MuxSelectorGenerator
from .mux_assembly import MuxAssemblyGenerator

# Motor mount generators
from .motor_mount_params import Motor130Params, MotorMountParams, ShaftCouplingParams
from .motor_mount_right import RightMotorMountGenerator
from .motor_mount_left import LeftMotorMountGenerator
from .shaft_coupling import ShaftCouplingGenerator
from .motor_assembly import MotorAssemblyGenerator
from .motor_housing import MotorHousingGenerator, MotorHousingParams

# Layout utilities
from .layout import LayoutCalculator, SelectorLayout, BevelLayout, HousingLayout, MuxLayout

__all__ = [
    # Part generators
    "LowerHousingGenerator",
    "UpperHousingGenerator",
    "ShiftLeverGenerator",
    "AxleGenerator",
    "DogClutchGenerator",
    "SpurGearGenerator",
    "BevelGearGenerator",

    "SerpentineFlexureGenerator",
    # Assembly generators
    "BevelPairGenerator",
    "BevelLeverGenerator",
    "BevelLeverWithUpperHousingGenerator",
    "SelectorMechanismGenerator",
    "SelectorWithHousingGenerator",
    "CombinedSelectorGenerator",
    "MuxSelectorGenerator",
    "MuxAssemblyGenerator",
    # Motor mount generators
    "Motor130Params",
    "MotorMountParams",
    "ShaftCouplingParams",
    "RightMotorMountGenerator",
    "LeftMotorMountGenerator",
    "ShaftCouplingGenerator",
    "MotorAssemblyGenerator",
    "MotorHousingGenerator",
    "MotorHousingParams",
    # Layout utilities
    "LayoutCalculator",
    "SelectorLayout",
    "BevelLayout",
    "HousingLayout",
    "MuxLayout",
]
