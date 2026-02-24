import boto3
import json
from infra_review_cli.config import REGION_LOCATION_MAP

# Hardcoded fallback monthly prices (in USD)
FALLBACK_PRICES = {
    "ebs_gp2": 0.10,         # per GB
    "ebs_gp3": 0.08,
    "elastic_ip": 3.65,      # $0.005/hr * 730
    "elb_application": 16.42, # $0.0225/hr * 730
    "elb_network": 16.42,
    "elb_classic": 18.25,     # $0.025/hr * 730
}

_PRICE_CACHE = {}

def get_ebs_price_per_gb(storage_type: str = "gp2", region: str = "us-east-1") -> float:
    """Return price per GB for EBS volume."""
    cache_key = f"ebs-{storage_type}-{region}"
    if cache_key in _PRICE_CACHE:
        return _PRICE_CACHE[cache_key]

    location = REGION_LOCATION_MAP.get(region, "US East (N. Virginia)")
    pricing = boto3.client("pricing", region_name="us-east-1")

    try:
        response = pricing.get_products(
            ServiceCode="AmazonEC2",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "volumeType", "Value": storage_type},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"},
            ],
            MaxResults=1
        )

        product = json.loads(response["PriceList"][0])
        on_demand = next(iter(product["terms"]["OnDemand"].values()))
        price_dimension = next(iter(on_demand["priceDimensions"].values()))
        price = float(price_dimension["pricePerUnit"]["USD"])
        _PRICE_CACHE[cache_key] = price
        return price

    except Exception:
        return FALLBACK_PRICES.get(f"ebs_{storage_type}", 0.10)


def get_elastic_ip_price(region: str) -> float:
    """Return monthly price for an unassociated Elastic IP."""
    return FALLBACK_PRICES["elastic_ip"]


def get_elb_price(region: str, lb_type: str = "application") -> float:
    """Return monthly base cost for an ELB."""
    return FALLBACK_PRICES.get(f"elb_{lb_type}", 16.42)


