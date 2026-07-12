"""
Broker providers — all implementations.
Automatically imports all provider classes and builds a provider map.
"""

# Import all broker provider classes
from .zerodha import ZerodhaProvider
from .upstox import UpstoxProvider
from .angelone import AngelOneProvider
from .icici import ICICIDirectProvider
from .hdfc import HDFCSecuritiesProvider
from .axis_direct import AxisDirectProvider
from .kotak import KotakProvider
from .kotak_neo import KotakNeoProvider
from .motilal import MotilalProvider
from .anand_rathi import AnandRathiProvider
from .edelweiss import EdelweissProvider
from .geojit import GeojitProvider
from .sharekhan import SharekhanProvider
from .sbi import SBISecuritiesProvider
from .sbi_sg import SBISGProvider
from .fyers import FyersProvider
from .fivepaisa import FivePaisaProvider
from .iifl import IIFLProvider
from .bajaj import BajajFinancialProvider
from .finvasia import FinvasiaProvider
from .aliceblue import AliceBlueProvider
from .choice import ChoiceProvider
from .master_trust import MasterTrustProvider
from .groww import GrowwProvider
from .paytm_money import PaytmMoneyProvider
from .mstock import MStockProvider
from .moneysukh import MoneysukhProvider
from .dolat import DolatProvider
from .swastika import SwastikaProvider
from .centrum import CentrumProvider
from .indiabulls import IndiabullsProvider
from .trustline import TrustlineProvider
from .smc import SMCProvider
from .ventura import VenturaProvider
from .gepl import GEPLProvider
from .samco import SamcoProvider
from .religare import ReligareProvider
from .ambit import AmbitProvider
from .jm_financial import JMFinancialProvider
from .kedia import KediaProvider
from .prabhu import PrabhuProvider
from .jainam import JainamProvider
from .marwadi import MarwadiProvider
from .shree_krishna import ShreeKrishnaProvider
from .investec import InvestecProvider
from .phillipcapital import PhillipCapitalProvider
from .tradejini import TradejiniProvider
from .bofa import BofaProvider
from .aditya_birla_money import AdityaBirlaMoneyProvider
from .jefferies import JefferiesProvider
from .clsa import CLSAProvider
from .yes_securities import YesSecuritiesProvider

# Map provider key -> class
_PROVIDER_MAP = {
    'zerodha': ZerodhaProvider,
    'upstox': UpstoxProvider,
    'angelone': AngelOneProvider,
    'icici': ICICIDirectProvider,
    'hdfc': HDFCSecuritiesProvider,
    'axis_direct': AxisDirectProvider,
    'kotak': KotakProvider,
    'kotak_neo': KotakNeoProvider,
    'motilal': MotilalProvider,
    'anand_rathi': AnandRathiProvider,
    'edelweiss': EdelweissProvider,
    'geojit': GeojitProvider,
    'sharekhan': SharekhanProvider,
    'sbi': SBISecuritiesProvider,
    'sbi_sg': SBISGProvider,
    'fyers': FyersProvider,
    'fivepaisa': FivePaisaProvider,
    'iifl': IIFLProvider,
    'bajaj': BajajFinancialProvider,
    'finvasia': FinvasiaProvider,
    'aliceblue': AliceBlueProvider,
    'choice': ChoiceProvider,
    'master_trust': MasterTrustProvider,
    'groww': GrowwProvider,
    'paytm_money': PaytmMoneyProvider,
    'mstock': MStockProvider,
    'moneysukh': MoneysukhProvider,
    # Stubs
    'dolat': DolatProvider,
    'swastika': SwastikaProvider,
    'centrum': CentrumProvider,
    'indiabulls': IndiabullsProvider,
    'trustline': TrustlineProvider,
    'smc': SMCProvider,
    'ventura': VenturaProvider,
    'gepl': GEPLProvider,
    'samco': SamcoProvider,
    'religare': ReligareProvider,
    'ambit': AmbitProvider,
    'jm_financial': JMFinancialProvider,
    'kedia': KediaProvider,
    'prabhu': PrabhuProvider,
    'jainam': JainamProvider,
    'marwadi': MarwadiProvider,
    'shree_krishna': ShreeKrishnaProvider,
    'investec': InvestecProvider,
    'phillipcapital': PhillipCapitalProvider,
    'tradejini': TradejiniProvider,
    'bofa': BofaProvider,
    'aditya_birla_money': AdityaBirlaMoneyProvider,
    'jefferies': JefferiesProvider,
    'clsa': CLSAProvider,
    'yes_securities': YesSecuritiesProvider,
}

__all__ = list(_PROVIDER_MAP.keys())