from typing import Union
from apps.exchange.models.price_log import CurrencyPriceLog

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from apps.exchange.exceptions.price_exceptions import InsufficientBuyAmount, InsufficientSellAmount


class PriceService:
    """
    This service class is responsible for calculating the price of XAU18 currency based on the latest price log and the transaction details.
    """

    @staticmethod
    def calculate_xau18_currency_price(unit: str, amount: Union[int, float, Decimal], transaction_type: str) -> dict:

        price_log = CurrencyPriceLog.objects.select_related('currency').filter(
            currency__symbol='XAU18').order_by('-id').first()

        currency = price_log.currency

        lowest_buy = currency.lowest_amount_buy
        lowest_sell = currency.lowest_amount_sell

        # Convert amount to Decimal for precise calculations
        amount = Decimal(str(amount))

        # Calculate gold amount based on the unit
        if unit == 'IRT':
            gold_amount = amount / price_log.price
        else:  # unit == 'XAU18'
            gold_amount = Decimal(amount)

        # Round down gold amount to 4 decimal places
        gold_amount = gold_amount.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

        if transaction_type == 'buy' and unit == 'IRT':

            # Check minimum buy amount
            if gold_amount < lowest_buy:
                raise InsufficientBuyAmount(f"مقدار درخواستی کمتر از حداقل مقدار قابل خرید است")

            while gold_amount > 0:

                # ------------------------------
                #   Calculate buy fee based on gold amount
                # ------------------------------
                if gold_amount < Decimal("0.5"):
                    buy_fee = currency.fixed_buy_fee_toman

                elif Decimal("0.5") <= gold_amount < Decimal("1"):

                    percent = currency.buy_fee_percent / Decimal("100")

                    fee_at_1g = price_log.price * Decimal("1") * percent

                    start_fee = currency.fixed_buy_fee_toman
                    end_fee = fee_at_1g

                    progress = (gold_amount - Decimal("0.5")) / Decimal("0.5")

                    buy_fee = start_fee + (end_fee - start_fee) * progress
                    buy_fee = buy_fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

                else:
                    percent = currency.buy_fee_percent / Decimal("100")
                    buy_fee = (price_log.price * gold_amount * percent)
                    buy_fee = buy_fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


                # ------------------------------
                #    Maintenance Fee
                # ------------------------------
                maintenance_fee = (currency.maintenance_fee * gold_amount).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )

                # ------------------------------
                #     Gold Price
                # ------------------------------
                gold_price_toman = (price_log.price * gold_amount).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )

                # ------------------------------
                #    Total Amount
                # ------------------------------
                total_amount = gold_price_toman + buy_fee + maintenance_fee

                # If total_amount is less than or equal to the original amount, we can break the loop
                if total_amount <= amount:
                    break

                # Deduct a small amount of gold and recalculate until total_amount is within the desired range
                gold_amount -= Decimal("0.0001")
                gold_amount = gold_amount.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

            net_amount = gold_price_toman

            response = {
                "message": "Success",
                "data": {
                    "amount": str(amount),
                    "total_amount": int(total_amount),
                    "gold_amount": str(gold_amount),
                    "maintenance_fee": int(maintenance_fee),
                    "net_amount": int(net_amount),
                    "fee_toman": int(buy_fee),
                    "price_per_gram": price_log.price,
                    "discount_amount": 0
                }
            }

            return response

        elif unit == 'XAU18' and transaction_type == 'sell':

            # Check minimum sell amount
            if gold_amount < lowest_sell:
                raise InsufficientSellAmount('مقدار درخواستی کمتر از حداقل مقدار قابل فروش است')

            # ------------------------------
            #   Calculate sell fee based on gold amount
            # ------------------------------
            if gold_amount < Decimal("0.5"):
                sell_fee = currency.fixed_sell_fee_toman

            elif Decimal("0.5") <= gold_amount < Decimal("1"):

                percent = currency.sell_fee_percent / Decimal("100")

                fee_at_1g = price_log.price * Decimal("1") * percent

                start_fee = currency.fixed_sell_fee_toman
                end_fee = fee_at_1g

                progress = (gold_amount - Decimal("0.5")) / Decimal("0.5")

                sell_fee = start_fee + (end_fee - start_fee) * progress
                sell_fee = sell_fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

            else:
                percent = currency.sell_fee_percent / Decimal("100")
                sell_fee = (price_log.price * gold_amount * percent)
                sell_fee = sell_fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

            # ------------------------------
            #     Gold Price (Round)
            # ------------------------------
            gold_price_toman = (price_log.price * gold_amount).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )

            # ------------------------------
            #    Final Total Amount
            # ------------------------------
            total_amount = gold_price_toman - sell_fee

            net_amount = gold_price_toman

            response = {
                "message": "Success",
                "data": {
                    "amount": str(amount),  
                    "total_amount": int(total_amount),  
                    "gold_amount": str(gold_amount),
                    "maintenance_fee": 0,   
                    "net_amount": int(net_amount),
                    "fee_toman": int(sell_fee),
                    "price_per_gram": price_log.price,
                    "discount_amount": 0
                }
            }

            return response
        
    @staticmethod
    def calculate_buy_total_from_snapshot(
        *,
        gold_amount: Decimal,
        unit_price_irt: Decimal,
        currency,
    ) -> dict:
        """
        This method calculates the total amount for a buy transaction based on a price snapshot.
        """

        gold_amount = Decimal(str(gold_amount))
        unit_price_irt = Decimal(str(unit_price_irt))

        # ------------------------------
        #     Gold Price
        # ------------------------------
        gold_price_toman = (unit_price_irt * gold_amount).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

        # ------------------------------
        # Calculate buy fee based on gold amount
        # ------------------------------
        if gold_amount < Decimal("0.5"):
            buy_fee = currency.fixed_buy_fee_toman

        elif Decimal("0.5") <= gold_amount < Decimal("1"):

            percent = currency.buy_fee_percent / Decimal("100")
            fee_at_1g = (unit_price_irt * Decimal("1") * percent)

            start_fee = currency.fixed_buy_fee_toman
            end_fee = fee_at_1g

            progress = (gold_amount - Decimal("0.5")) / Decimal("0.5")
            buy_fee = start_fee + (end_fee - start_fee) * progress
            buy_fee = buy_fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        else:
            percent = currency.buy_fee_percent / Decimal("100")
            buy_fee = (unit_price_irt * gold_amount * percent)
            buy_fee = buy_fee.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        # ------------------------------
        #    maintenance fee
        # ------------------------------
        maintenance_fee = (currency.maintenance_fee * gold_amount).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

        # ------------------------------
        #     total
        # ------------------------------
        total_amount = gold_price_toman + buy_fee + maintenance_fee

        return {
            "gold_price": int(gold_price_toman),
            "fee": int(buy_fee),
            "maintenance": int(maintenance_fee),
            "total": int(total_amount),
        }