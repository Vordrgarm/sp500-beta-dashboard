from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

SP500 = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","BRK-B","JPM","LLY",
    "V","UNH","XOM","MA","AVGO","PG","JNJ","HD","COST","MRK",
    "ABBV","CVX","CRM","BAC","NFLX","PEP","KO","TMO","WMT","ACN",
    "MCD","ABT","CSCO","LIN","TXN","DHR","NEE","PM","ADBE","AMD",
    "DIS","INTU","WFC","CAT","GE","RTX","AMGN","ISRG","SPGI","HON"
]

STOCK_ANALYSIS = {
    "AAPL": {
        "current": "Apple trades at a premium valuation with a beta that has moderated in recent years, reflecting its maturation from a high-growth tech company into a stable cash-flow machine. Its services segment now provides revenue predictability that dampens market sensitivity.",
        "historical": "During the 2008 financial crisis, Apple's beta spiked as it was still perceived as a cyclical consumer electronics company. Post-2012, as the iPhone became a staple product, beta declined steadily. The COVID crash briefly elevated beta before the work-from-home boom drove massive outperformance. The 2022 rate hike cycle compressed its multiple but beta remained moderate, reflecting defensive qualities of its loyal installed base."
    },
    "MSFT": {
        "current": "Microsoft's beta reflects its dual identity as both a mature enterprise software provider and a high-growth cloud company. Azure's rapid expansion keeps beta above pure defensives, while its recurring revenue model anchors it below pure cyclicals.",
        "historical": "Microsoft spent much of the 2010s with a low beta as it was seen as a slow-growth legacy software company. Satya Nadella's cloud pivot from 2014 onward gradually pushed beta higher as growth expectations increased. The 2022 rate hike cycle hit growth stocks hard, temporarily elevating beta, but its cash generation capability kept it resilient."
    },
    "NVDA": {
        "current": "NVIDIA currently carries one of the highest betas in the S&P 500, driven by extreme sensitivity to AI infrastructure spending cycles and semiconductor demand. Its valuation is priced for extraordinary growth, making it highly reactive to any shifts in AI sentiment.",
        "historical": "Prior to 2016, NVIDIA was a mid-tier graphics chip company with moderate beta. The cryptocurrency boom of 2017-2018 caused its first major beta spike. After crypto collapsed, beta fell. The AI boom starting in 2023 pushed NVIDIA to unprecedented valuations, making it the most volatile mega-cap in the index."
    },
    "AMZN": {
        "current": "Amazon's beta reflects the tension between its defensive e-commerce business and its high-growth AWS cloud segment. The market increasingly prices Amazon as a cloud company, keeping beta elevated relative to traditional retailers.",
        "historical": "Amazon has historically carried a high beta due to its persistent reinvestment strategy and low margins. During 2008, it sold off sharply with the market. The pandemic was uniquely beneficial, briefly reducing beta as e-commerce demand surged regardless of economic conditions. The 2022 rate hike cycle hit it hard as rising rates compress high-multiple growth stocks."
    },
    "META": {
        "current": "Meta's beta has stabilized after a turbulent few years. Its advertising revenue model is highly cyclical — companies cut ad budgets in recessions — keeping beta above 1. Its Reality Labs losses and AI investments add uncertainty that elevates beta further.",
        "historical": "Meta went public in 2012 with a moderate beta that rose steadily through the mid-2010s as it became a dominant ad platform. The 2018 Cambridge Analytica scandal and iOS privacy changes in 2021 caused idiosyncratic volatility separate from market movements. The 2022 'Year of Efficiency' selloff was one of the most severe for any mega-cap, briefly pushing beta to extremes."
    },
    "GOOGL": {
        "current": "Alphabet's beta reflects its dominant but maturing advertising business, offset by high-growth cloud and AI investments. Its strong balance sheet and cash generation provide a floor that keeps beta from reaching pure growth-stock levels.",
        "historical": "Google has maintained a relatively stable mid-range beta throughout its public history. Its advertising duopoly with Meta provides durable revenue but cyclical sensitivity. The 2022 rate hike cycle elevated beta as growth multiples compressed. AI competition concerns from ChatGPT briefly introduced new uncertainty into its beta profile."
    },
    "TSLA": {
        "current": "Tesla carries one of the highest betas in the index, driven by its CEO's public profile, intense retail investor participation, and the high-growth electric vehicle narrative. It trades more like a technology company than an automaker.",
        "historical": "Tesla's beta has been consistently high since its inclusion in the S&P 500 in 2020. Its stock nearly tripled in 2020 alone, creating massive upside beta. The 2022 selloff was brutal, with the stock losing over 60% as rate hikes hammered growth valuations. Political controversy around Elon Musk in 2024-2025 added further idiosyncratic volatility."
    },
    "BRK-B": {
        "current": "Berkshire Hathaway has one of the lowest betas in the index. Its diversified conglomerate structure spanning insurance, railroads, energy, and consumer brands provides natural hedging. Its massive cash reserves act as a further stabilizer.",
        "historical": "Berkshire has maintained a low beta across all major market events. During the 2008 financial crisis, its insurance operations and conservative balance sheet allowed it to deploy capital while others were deleveraging. The COVID crash saw a brief beta spike but its defensive businesses quickly stabilized. It represents the archetype of a low-beta defensive compounder."
    },
    "JPM": {
        "current": "JPMorgan's beta reflects the inherent cyclicality of banking — loan growth, credit losses, and net interest margins all move with the economic cycle. As the largest US bank, it is a bellwether for financial sector health.",
        "historical": "During the 2008 financial crisis, JPMorgan's beta spiked dramatically as systemic banking risk was priced in. Despite being one of the stronger banks through the crisis, it still moved sharply with the sector. Post-crisis regulatory capital requirements improved stability and reduced beta. The 2022 rate hike cycle was initially positive for banks but then concerns about regional bank failures in 2023 temporarily elevated beta again."
    },
    "LLY": {
        "current": "Eli Lilly has experienced a dramatic beta compression as GLP-1 drugs (Ozempic, Mounjaro) transformed it from a traditional pharmaceutical company into a high-growth blockbuster story. Its pipeline visibility has made it one of the most sought-after defensive growth stocks.",
        "historical": "Historically Eli Lilly carried a typical low healthcare beta below 0.8. The emergence of GLP-1 obesity and diabetes drugs post-2021 completely changed its profile — it now combines healthcare defensiveness with tech-like growth expectations, creating an unusual low-beta, high-momentum combination."
    },
    "V": {
        "current": "Visa's beta reflects its position as a toll-booth on global consumer spending. Its asset-light model and lack of credit risk keeps beta moderate, while its dependence on consumer spending volume maintains some cyclicality.",
        "historical": "Visa went public in 2008 at the worst possible time but demonstrated remarkable resilience. Its beta has been consistently moderate — not purely defensive like utilities, but well below the market. The COVID crash was uniquely painful as cross-border transactions collapsed, temporarily spiking beta. Recovery was swift as digital payments accelerated."
    },
    "UNH": {
        "current": "UnitedHealth Group currently faces elevated uncertainty from regulatory and political pressure on managed care organizations, which has raised its beta above historical norms. Underlying healthcare demand remains defensive but political risk adds a new volatility dimension.",
        "historical": "UnitedHealth has historically been a low-beta healthcare compounder. Its managed care model provides revenue predictability that insulates it from economic cycles. The stock's beta rose in 2024-2025 due to regulatory investigations and the tragic death of its CEO, introducing idiosyncratic risk not present in prior cycles."
    },
    "XOM": {
        "current": "ExxonMobil's current beta is unusually low given energy sector history, reflecting the market's view that the company has matured its capital allocation. However, oil price sensitivity remains the dominant driver of its stock movements.",
        "historical": "Exxon's beta has historically tracked oil price cycles closely. The 2014-2016 oil price collapse caused significant underperformance. The COVID crash briefly made it inverse to the market as oil went negative. The 2021-2022 energy supercycle dramatically improved its financial position and reduced perceived risk."
    },
    "MA": {
        "current": "Mastercard shares Visa's toll-booth business model characteristics, maintaining a moderate beta anchored by its asset-light structure and recurring transaction fee revenue. Consumer spending trends and cross-border travel volume are its key beta drivers.",
        "historical": "Mastercard's beta history closely mirrors Visa's. It has been a consistent moderate-beta compounder with spikes during the 2020 COVID crash when cross-border volumes collapsed. Its premium valuation means rate sensitivity is higher than its stable revenues would otherwise suggest."
    },
    "AVGO": {
        "current": "Broadcom carries a high beta driven by its exposure to hyperscaler AI chip demand and semiconductor cycles. The VMware acquisition has added software revenues that may moderate beta over time as integration completes.",
        "historical": "Broadcom built its current scale through aggressive M&A, and each major acquisition temporarily elevated beta as integration risk was priced in. The AI infrastructure buildout starting in 2023 significantly raised its beta as it became a key beneficiary of custom AI chip demand from major cloud providers."
    },
    "PG": {
        "current": "Procter & Gamble is the definition of a defensive low-beta stock. Its portfolio of essential household brands generates stable cash flows regardless of economic conditions, making it a classic flight-to-safety asset during downturns.",
        "historical": "P&G has maintained sub-0.5 beta through virtually every major market event. During the 2008 crisis and COVID crash, it actually attracted capital as investors sought safety, briefly creating near-zero or negative correlation with the market. The 2022 rate hike cycle was an exception — rising rates hit high-yield-substitute defensives, temporarily raising its beta."
    },
    "JNJ": {
        "current": "Johnson & Johnson's beta has been affected by the talc litigation overhang and the separation of its consumer health business (Kenvue). As a pure pharmaceutical and medical device company, it retains strong defensive characteristics.",
        "historical": "J&J has been a benchmark low-beta healthcare stock for decades. Its diversified business model across pharmaceuticals, medical devices, and consumer health provided natural hedging. The talc litigation introduced legal risk that added some idiosyncratic volatility, while the Kenvue spinoff in 2023 slightly changed its risk profile."
    },
    "HD": {
        "current": "Home Depot's beta reflects its sensitivity to the housing market and consumer discretionary spending. High interest rates have been a significant headwind by suppressing existing home sales and renovation activity, adding cyclical pressure.",
        "historical": "Home Depot's beta has historically tracked housing market cycles closely. The 2008 financial crisis was devastating as the housing collapse was its core business headwind. The COVID pandemic created an unusual boom as stay-at-home consumers invested in home improvement, briefly lowering beta through outperformance. The 2022 rate hike cycle reversed this as mortgage rates killed housing turnover."
    },
    "COST": {
        "current": "Costco's membership model creates recurring revenue that insulates it from economic downturns — members continue shopping regardless of conditions. This makes it one of the most defensive retailers, with a beta that frequently approaches zero.",
        "historical": "Costco has consistently demonstrated low beta across all market cycles. Its warehouse model and membership loyalty provide unusual stability for a consumer discretionary company. During recessions, consumers often trade down to bulk buying, making Costco somewhat counter-cyclical. Its low beta makes it a core holding for risk-averse equity investors."
    },
    "MRK": {
        "current": "Merck's beta is anchored by its oncology franchise, particularly Keytruda, which provides visibility into long-term cash flows. Its defensive pharmaceutical characteristics are partially offset by binary drug approval risks.",
        "historical": "Merck has maintained a consistently low beta throughout its history as a major pharmaceutical company. Healthcare demand is relatively inelastic to economic conditions. Patent cliffs have historically been the primary stock-specific risk. The Keytruda franchise has significantly improved revenue visibility and further compressed beta in recent years."
    },
    "ABBV": {
        "current": "AbbVie's beta reflects the tension between its defensive healthcare positioning and the post-Humira revenue cliff risk. Its successful diversification into Skyrizi and Rinvoq has helped maintain investor confidence and keep beta low.",
        "historical": "AbbVie was spun off from Abbott in 2013 with significant Humira dependence. Beta was moderate as investors priced biosimilar risk. The successful launch of next-generation immunology drugs provided confidence that partially offset the Humira patent cliff, keeping beta lower than the revenue concentration risk would otherwise suggest."
    },
    "CVX": {
        "current": "Chevron's beta is driven almost entirely by oil and gas price cycles. Its integrated business model and strong balance sheet provide some buffer, but energy commodity sensitivity remains the dominant factor in its stock movements.",
        "historical": "Chevron's beta has tracked major energy cycles closely. The 2014-2016 oil collapse was damaging. COVID sent oil prices negative briefly, creating extreme volatility. The 2021-2022 energy supercycle boosted the stock dramatically. The Hess acquisition added uncertainty. Recent oil price weakness amid recession fears has weighed on the stock."
    },
    "CRM": {
        "current": "Salesforce's beta has moderated from its peak growth years as the company has shifted focus toward profitability over growth. However, its high valuation relative to current earnings keeps it sensitive to interest rate movements and growth expectations.",
        "historical": "Salesforce carried a very high beta during its high-growth phase in the 2010s when it was expanding aggressively and posting consistent losses. As it matured and became profitable, beta moderated. The 2022 rate hike cycle hit it hard as rising rates compress high-multiple growth stocks."
    },
    "BAC": {
        "current": "Bank of America's beta closely tracks the US economic cycle. Its large consumer banking and investment banking operations make it highly sensitive to credit cycles, interest rates, and capital markets activity.",
        "historical": "Bank of America had one of the most extreme beta spikes during the 2008 financial crisis due to its Countrywide mortgage acquisition exposure. It required government support and spent years rebuilding capital. Post-crisis, beta normalized as the balance sheet was repaired. The 2022 rate hike cycle initially helped net interest margins but long-duration bond losses created new concerns."
    },
    "NFLX": {
        "current": "Netflix's beta has been highly variable, driven by subscriber growth metrics that the market treats as the primary valuation driver. Its advertising tier and password-sharing crackdown have improved financial visibility, moderating beta from its peak levels.",
        "historical": "Netflix has historically been one of the highest-beta stocks in the S&P 500. Its subscriber-driven valuation model means any growth miss causes outsized stock reactions. The 2022 subscriber loss was catastrophic — the stock lost over 70% — before recovering sharply in 2023. Beta remains elevated as growth expectations are still priced in at premium multiples."
    },
    "PEP": {
        "current": "PepsiCo's diversified snack and beverage portfolio makes it one of the most defensive consumer staples companies. Volume pressure from GLP-1 drug adoption is a new secular risk that has slightly elevated beta from historical lows.",
        "historical": "PepsiCo has maintained a very low beta throughout its history. Its global brand portfolio and pricing power provide stability across economic cycles. The company was essentially flat or positive during the 2008 financial crisis. Recent concerns about GLP-1 drugs reducing snack consumption have introduced a new source of long-term uncertainty."
    },
    "KO": {
        "current": "Coca-Cola is one of the most classic defensive stocks in the market, carrying a near-zero beta in many periods. Its global brand, pricing power, and dividend history make it the archetypical flight-to-safety equity.",
        "historical": "Coca-Cola has maintained sub-0.5 beta through virtually every market crisis in modern history. During 2008 and the COVID crash, it attracted capital as a safe haven. Like other high-yield defensives, it faced headwinds in 2022 as rising interest rates made bonds more competitive. Warren Buffett's long-term holding has become a symbol of the company's stability."
    },
    "TMO": {
        "current": "Thermo Fisher's beta reflects its position as a pick-and-shovel supplier to the life sciences industry. Revenue visibility from long-term research contracts provides stability, while bioproduction cyclicality adds some market sensitivity.",
        "historical": "Thermo Fisher built its current scale through consistent M&A in life sciences tools. Beta has been moderate through most of its history. The COVID pandemic was a significant tailwind as testing and vaccine production demand surged, briefly pushing it into a negative correlation with market stress. Post-COVID normalization has brought beta back toward its long-run mean."
    },
    "WMT": {
        "current": "Walmart's beta is among the lowest in the consumer sector. Its essential retail model attracts shoppers in all economic conditions, and its massive private label and grocery footprint make it particularly resilient in downturns.",
        "historical": "Walmart has been a classic counter-cyclical defensive stock. During the 2008 crisis, it outperformed significantly as consumers traded down. The COVID pandemic saw initial panic-buying surges followed by normalization. Its e-commerce investments have added growth expectations that slightly elevated beta from historical lows. Recent strong performance amid recession fears has further compressed beta."
    },
    "ACN": {
        "current": "Accenture's beta reflects its consulting and IT services model, which provides revenue stability through long-term contracts but is ultimately dependent on corporate IT spending — a discretionary budget item that gets cut in recessions.",
        "historical": "Accenture has maintained a moderate beta throughout its history. Corporate IT consulting tends to be semi-discretionary — companies cut spending in deep recessions but maintain essential transformation projects. The AI consulting boom has added a new growth driver but also raised valuation-related rate sensitivity."
    },
    "MCD": {
        "current": "McDonald's carries one of the lowest betas among consumer companies. Its franchise model generates relatively stable royalty income, and its value positioning attracts consumers during economic downturns when they trade down from sit-down restaurants.",
        "historical": "McDonald's has been a consistent low-beta defensive stock. During 2008, it outperformed as consumers traded down. The COVID pandemic initially disrupted it as dining rooms closed, but drive-through and delivery sustained performance. Recent price increases have created affordability concerns but its value-tier menu remains competitive."
    },
    "ABT": {
        "current": "Abbott's beta reflects its diversified medical device and diagnostics portfolio. Post-COVID normalization has been a headwind as its COVID testing revenue collapsed, but the underlying device business remains stable.",
        "historical": "Abbott spun off AbbVie in 2013 to focus on medical devices and diagnostics. Beta has been consistently moderate-low as healthcare demand is relatively inelastic. COVID testing revenue in 2020-2022 created unusual revenue patterns. The post-COVID revenue cliff from diagnostic testing was a significant but temporary beta-elevating event."
    },
    "CSCO": {
        "current": "Cisco's beta has declined as the company has transformed from a pure hardware company into a software and subscription-driven business. Its recurring revenue model and strong balance sheet provide defensive characteristics.",
        "historical": "Cisco was one of the most extreme beta stories in history — its dot-com bubble collapse saw it lose over 80% of its value. Post-bubble, it spent years rebuilding and its beta declined significantly. Its transformation to software and subscriptions has further moderated beta as revenue predictability improved."
    },
    "LIN": {
        "current": "Linde's industrial gas business is highly defensive — gases are essential inputs for manufacturing, healthcare, and energy, with long-term take-or-pay contracts providing revenue visibility that anchors a below-market beta.",
        "historical": "Linde has maintained a consistently low beta through its history. Industrial gas distribution is one of the most stable chemical businesses due to the critical nature of the product and high switching costs. The merger with Praxair in 2018 created the world's largest industrial gas company and further improved its diversification and stability."
    },
    "TXN": {
        "current": "Texas Instruments' beta reflects the semiconductor cycle sensitivity balanced against its high-margin analog chip focus. Its free cash flow discipline and return-of-capital commitment provide defensive characteristics unusual for the semiconductor sector.",
        "historical": "Texas Instruments has undergone a significant strategic transformation over the past decade, exiting mobile chips to focus on industrial and automotive analog semiconductors. This shift toward more stable end markets has reduced beta compared to more cyclical peers. The semiconductor super-cycle of 2020-2021 and subsequent correction provided a clear demonstration of remaining cyclicality."
    },
    "DHR": {
        "current": "Danaher's beta reflects its life sciences and diagnostics focus, with revenue stability from recurring consumables offsetting some equipment cycle exposure. Its Fortive spinoff and post-COVID diagnostics normalization have been key factors in recent beta movements.",
        "historical": "Danaher built a reputation as a consistent compounder through serial M&A and operational improvement. Beta was generally moderate through most of its history. The COVID pandemic dramatically boosted its diagnostics revenues, temporarily creating negative market correlation. Post-COVID normalization created a significant earnings headwind that has modestly elevated beta."
    },
    "NEE": {
        "current": "NextEra Energy's beta is unusually high for a utility due to its large renewable energy development pipeline, which carries project risk and is rate-sensitive. It combines utility defensiveness with growth company characteristics.",
        "historical": "NextEra has maintained higher beta than traditional utilities due to its aggressive renewable energy expansion. The 2022 rate hike cycle was particularly damaging — utilities are valued as bond proxies, and rising rates made their dividend yields less attractive, causing significant underperformance. Its Florida Power & Light subsidiary provides a stable regulated base."
    },
    "PM": {
        "current": "Philip Morris International's beta is near zero, reflecting the highly addictive nature of its products and the geographic diversification of its revenue across emerging and developed markets outside the United States.",
        "historical": "Philip Morris has been a classic near-zero-beta stock due to the inelastic demand for tobacco products. During every major market crisis, its dividend yield and revenue stability have attracted defensive capital. The pivot toward smoke-free products (IQOS) has added some growth uncertainty but has not materially changed its beta profile."
    },
    "ADBE": {
        "current": "Adobe's beta reflects its high-quality subscription software model offset by significant AI disruption risk. The failed Figma acquisition and concerns about AI-generated content threatening its creative suite franchise have introduced new uncertainties.",
        "historical": "Adobe successfully transitioned from perpetual license to subscription software in 2013, improving revenue predictability and initially reducing beta. However, its premium growth valuation kept it rate-sensitive. The AI inflection of 2023 created both opportunity and existential risk narratives that have kept beta elevated."
    },
    "AMD": {
        "current": "AMD carries one of the highest betas in the index, driven by intense competition with NVIDIA in AI chips, semiconductor cycle volatility, and a high valuation that makes it extremely sensitive to growth expectation changes.",
        "historical": "AMD spent most of its modern history as a struggling competitor to Intel and NVIDIA with extreme volatility and high beta. CEO Lisa Su's turnaround starting around 2016 transformed it into a credible competitor. Each product cycle creates massive stock moves. The AI chip race against NVIDIA has become the dominant narrative, keeping beta at elevated levels."
    },
    "DIS": {
        "current": "Disney's beta is elevated by the complexity of its business model transformation — managing the decline of traditional linear TV while building its streaming business, all while its theme parks provide the most stable cash flow segment.",
        "historical": "Disney's beta spiked dramatically during COVID as theme parks completely shut down — it was one of the most directly impacted large-cap companies. The streaming wars investment phase burned significant cash and elevated beta. The battle with activist investors and leadership changes added further idiosyncratic volatility."
    },
    "INTU": {
        "current": "Intuit's beta reflects its dominant position in tax preparation and small business accounting software, with high switching costs that provide revenue stability, offset by a growth valuation that creates rate sensitivity.",
        "historical": "Intuit has maintained a moderate-to-high beta as a premium-valued software company. Its annual tax season creates revenue predictability but the stock trades on long-term growth narratives. The Credit Karma acquisition expanded its total addressable market significantly. AI integration into its tax and accounting products is a key current growth driver."
    },
    "WFC": {
        "current": "Wells Fargo's beta reflects typical large-bank cyclicality, though its long-running Federal Reserve asset cap — imposed after the fake accounts scandal — has limited its growth and kept it somewhat undervalued relative to peers.",
        "historical": "Wells Fargo was deeply involved in the 2008 crisis through its Wachovia acquisition. The 2016 fake accounts scandal introduced severe regulatory and reputational risk, causing persistent beta elevation. The Fed asset cap has been a unique ongoing headwind. Removal of the cap, expected in coming years, could be a significant catalyst."
    },
    "CAT": {
        "current": "Caterpillar is a classic cyclical industrial with high beta tied to global construction, mining, and infrastructure spending. Its stock is widely used as a proxy for global economic activity and emerging market capex cycles.",
        "historical": "Caterpillar's beta has consistently tracked global economic cycles. The 2008 crisis was severe as construction and mining investment collapsed globally. The China infrastructure boom of 2009-2013 was a major tailwind. Trade war tensions in 2018-2019 created supply chain headwinds. Infrastructure spending legislation in 2021-2022 provided a significant boost."
    },
    "GE": {
        "current": "GE Aerospace — after the GE conglomerate breakup — is now a focused aerospace engine manufacturer with strong aftermarket services revenues. Its beta reflects commercial aerospace recovery cycles and defense spending.",
        "historical": "General Electric's beta history is extraordinary. It was once the world's most valuable company with a low-beta financial conglomerate structure. The GE Capital exposure in 2008 nearly destroyed the company, causing an extreme beta spike. The subsequent decade of restructuring, asset sales, and finally the three-way breakup (GE Aerospace, GE Vernova, GE HealthCare) has fundamentally changed its risk profile."
    },
    "RTX": {
        "current": "RTX Corporation's beta is moderated by its defense business — government contracts provide stable revenue regardless of economic conditions — balanced against its commercial aerospace exposure through the Pratt & Whitney engine business.",
        "historical": "RTX (formerly Raytheon Technologies) was formed by the merger of Raytheon and United Technologies in 2020, just as COVID hit the commercial aerospace sector. The Pratt & Whitney GTF engine powder metal contamination issue in 2023 created a significant unexpected cost and elevated beta. Defense budget growth remains a stable long-term anchor."
    },
    "AMGN": {
        "current": "Amgen's beta is anchored by its mature biopharmaceutical franchise, with relatively predictable revenues from established biologics and a growing biosimilars business. Its high dividend and shareholder return program adds defensive characteristics.",
        "historical": "Amgen has maintained low beta throughout its history as one of the original biotechnology companies that transitioned to a mature, profitable state. Its large molecule biologics have long patent lives and high barriers to biosimilar entry. The Horizon Therapeutics acquisition in 2023 expanded its rare disease portfolio."
    },
    "ISRG": {
        "current": "Intuitive Surgical's beta reflects its dominance in robotic surgery — high switching costs and procedure volumes that grow with aging demographics provide defensiveness, but premium valuation creates rate sensitivity.",
        "historical": "Intuitive Surgical has maintained moderate-to-high beta as a premium growth healthcare company. The da Vinci system has created a remarkable installed base with recurring instrument and service revenues. COVID disrupted elective surgeries significantly in 2020, causing a temporary beta spike. The introduction of the da Vinci 5 has renewed the growth cycle."
    },
    "SPGI": {
        "current": "S&P Global's beta reflects its critical role in financial markets — credit ratings, indices, and data analytics revenues are tied to capital market activity, which is cyclical, though its recurring subscription revenues provide a stable base.",
        "historical": "S&P Global has evolved from a traditional ratings agency into a diversified financial data and analytics company, particularly after the IHS Markit merger in 2022. The ratings business saw a significant boom in debt issuance during 2020-2021 low-rate environment. Rising rates in 2022 crushed debt issuance, a headwind for ratings revenue."
    },
    "HON": {
        "current": "Honeywell's beta reflects its diversified industrial portfolio spanning aerospace, building technologies, performance materials, and safety solutions. Its balanced exposure provides natural hedging across economic cycles.",
        "historical": "Honeywell has maintained a consistently moderate beta as a well-managed diversified industrial conglomerate. Its aerospace segment provides some defense-related stability while its building and industrial segments are more cyclical. The company has been an active portfolio manager, spinning off divisions to improve focus and returns."
    }
}

def calc_beta(returns_stock, returns_market):
    if len(returns_stock) < 12:
        return None
    cov = np.cov(returns_stock, returns_market)[0][1]
    var = np.var(returns_market, ddof=1)
    return round(cov / var, 4) if var != 0 else None

@app.route('/')
def serve_frontend():
    return send_from_directory('frontend', 'index.html')

@app.route("/beta")
def get_bulk_beta():
    tickers = SP500 + ["^GSPC"]
    raw     = yf.download(tickers, period="5y", auto_adjust=True, progress=False)["Close"]
    monthly = raw.resample("ME").last()
    returns = monthly.pct_change().dropna()
    market  = returns["^GSPC"]

    results = []
    for t in SP500:
        if t not in returns.columns:
            continue
        b_calc = calc_beta(returns[t].values, market.values)
        try:
            info   = yf.Ticker(t).info
            b_yf   = info.get("beta")
            name   = info.get("shortName", t)
            sector = info.get("sector", "Unknown")
        except:
            b_yf, name, sector = None, t, "Unknown"

        analysis = STOCK_ANALYSIS.get(t, {})
        results.append({
            "ticker":           t,
            "name":             name,
            "sector":           sector,
            "beta_calc":        b_calc,
            "beta_yahoo":       round(b_yf, 4) if b_yf else None,
            "delta":            round(abs(b_calc - b_yf), 4) if (b_calc and b_yf) else None,
            "analysis_current": analysis.get("current", ""),
            "analysis_history": analysis.get("historical", ""),
            "verify_url":       f"https://finance.yahoo.com/quote/{t}/key-statistics/",
            "timestamp":        datetime.now().isoformat()
        })

    return jsonify(sorted(results, key=lambda x: x["ticker"]))

@app.route("/beta/single")
def get_single_beta():
    ticker = request.args.get("ticker", "AAPL").upper()

    raw_max  = yf.download([ticker, "^GSPC"], period="max", auto_adjust=True, progress=False)["Close"]
    monthly  = raw_max.resample("ME").last()
    returns  = monthly.pct_change().dropna()

    years_available = round((returns.index[-1] - returns.index[0]).days / 365.25, 1)

    last_60 = returns.tail(60)
    b_calc  = calc_beta(last_60[ticker].values, last_60["^GSPC"].values) if ticker in last_60.columns else None

    # Rolling beta — 5-year window stepped back 1 year at a time
    rolling_betas = []
    end_idx = len(returns)
    window  = 60
    while end_idx >= window:
        wd        = returns.iloc[end_idx - window : end_idx]
        snap_beta = calc_beta(wd[ticker].values, wd["^GSPC"].values)
        snap_date = str(returns.index[end_idx - 1].date())
        if snap_beta is not None:
            rolling_betas.append({"date": snap_date, "beta": snap_beta})
        end_idx -= 12
    rolling_betas.reverse()

    monthly_hist    = returns[ticker].tail(60) if ticker in returns.columns else pd.Series()
    monthly_returns = [
        {"date": str(d.date()), "return": round(v * 100, 2)}
        for d, v in monthly_hist.items()
    ]

    info     = yf.Ticker(ticker).info
    analysis = STOCK_ANALYSIS.get(ticker, {})

    return jsonify({
        "ticker":           ticker,
        "name":             info.get("shortName"),
        "sector":           info.get("sector"),
        "beta_calc":        b_calc,
        "beta_yahoo":       round(info.get("beta"), 4) if info.get("beta") else None,
        "price":            info.get("currentPrice"),
        "marketCap":        info.get("marketCap"),
        "high52":           info.get("fiftyTwoWeekHigh"),
        "low52":            info.get("fiftyTwoWeekLow"),
        "years_available":  years_available,
        "rolling_betas":    rolling_betas,
        "monthly_returns":  monthly_returns,
        "analysis_current": analysis.get("current", ""),
        "analysis_history": analysis.get("historical", ""),
        "verify_url":       f"https://finance.yahoo.com/quote/{ticker}/key-statistics/",
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)