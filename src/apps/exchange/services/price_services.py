from typing import Union
from apps.exchange.models.price_log import CurrencyPriceLog

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from apps.exchange.exceptions.price_exceptions import InsufficientBuyAmount, InsufficientSellAmount


class PriceService:

    @staticmethod
    def calculate_currency_price(unit: str, amount: Union[int, float, Decimal], transaction_type: str) -> dict:

        price_log = CurrencyPriceLog.objects.select_related('currency').filter(
            currency__symbol='XAU18').order_by('-id').first()

        currency = price_log.currency

        lowest_buy = currency.lowest_amount_buy
        lowest_sell = currency.lowest_amount_sell

        # تبدیل اولیه amount به Decimal
        amount = Decimal(str(amount))

        # محاسبه مقدار طلا
        if unit == 'IRT':
            gold_amount = amount / price_log.price
        else:  # unit == 'XAU18'
            gold_amount = Decimal(amount)

        # رند اولیه رو به پایین - 4 رقم اعشار
        gold_amount = gold_amount.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

        if transaction_type == 'buy' and unit == 'IRT':

            # چک حداقل خرید
            if gold_amount < lowest_buy:
                raise InsufficientBuyAmount(f"مقدار درخواستی کمتر از حداقل مقدار قابل خرید است")

            while gold_amount > 0:

                # ------------------------------
                #   محاسبه کارمزد خرید
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
                #    هزینه نگهداری (Round)
                # ------------------------------
                maintance_fee = (currency.maintance_fee * gold_amount).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )

                # ------------------------------
                #     قیمت خود طلا
                # ------------------------------
                gold_price_toman = (price_log.price * gold_amount).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )

                # ------------------------------
                #    مبلغ کل
                # ------------------------------
                total_amount = gold_price_toman + buy_fee + maintance_fee

                # اگر مبلغ کل در محدوده بود → پایان حلقه
                if total_amount <= amount:
                    break

                # کم کردن 0.0001 گرم
                gold_amount -= Decimal("0.0001")
                gold_amount = gold_amount.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)

            net_amount = gold_price_toman

            response = {
                "message": "Success",
                "data": {
                    "amount": str(amount),
                    "total_amount": int(total_amount),
                    "gold_amount": str(gold_amount),
                    "maintenance_fee": int(maintance_fee),
                    "net_amount": int(net_amount),
                    "fee_toman": int(buy_fee),
                    "price_per_gram": price_log.price,
                    "discount_amount": 0
                }
            }

            return response

        elif unit == 'XAU18' and transaction_type == 'sell':

            # چک حداقل فروش
            if gold_amount < lowest_sell:
                raise InsufficientSellAmount('مقدار درخواستی کمتر از حداقل مقدار قابل فروش است')

            # ------------------------------
            #   محاسبه کارمزد فروش
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
            #     قیمت طلا (Round)
            # ------------------------------
            gold_price_toman = (price_log.price * gold_amount).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )

            # ------------------------------
            #    مبلغ نهایی دریافتی کاربر
            # ------------------------------
            total_amount = gold_price_toman - sell_fee

            net_amount = gold_price_toman

            response = {
                "message": "Success",
                "data": {
                    "amount": str(amount),   # مقدار گرم واردشده
                    "total_amount": int(total_amount),   # مبلغ دریافتی
                    "gold_amount": str(gold_amount),
                    "maintenance_fee": 0,     # در SELL وجود ندارد
                    "net_amount": int(net_amount),
                    "fee_toman": int(sell_fee),
                    "price_per_gram": price_log.price,
                    "discount_amount": 0
                }
            }

            return response