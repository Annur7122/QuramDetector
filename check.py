import re
from fuzzywuzzy import fuzz

# 🟢 Ingredient Lists
ALL_INGREDIENTS = {
    "haram": {
        "Кошениль/карминовая кислота", "Тартрат кальция", "Экстракт Квиллайи",
        "Аденозин 5'-монофосфат", "Алкоголь как растворитель для придания аромата",
        "Алкоголь в сухой форме в качестве ингредиента", "Бекон", "Кусочки бекона",
        "Бальзамический уксус", "Пиво", "Ароматизатор пива", "Экстракт пивных дрожжей",
        "Пивные дрожжи", 'E120', 'E103', 'E121', 'E125', 'E129', 'E182', 'E240',
        'E313', 'E314', 'E324', 'E388', 'E389', 'E390', 'E391', 'E399h', 'E425',
        'E479', 'E480', 'E484', 'E485', 'E486', 'E487', 'E488', 'E489', 'E496',
        'E505', 'E537', 'E538', 'E557', 'E626', 'E700', 'E701', 'E710', 'E711',
        'E712', 'E713', 'E714', 'E715', 'E716', 'E717', 'E906', 'E918', 'E919',
        'E922', 'E923', 'E929', 'E940', 'E946', 'E904', 'E1000', 'E1001', 'E1510'
    },
    "suspected": {
        "Глицерин", "Желатин", "Эфиры глицерина и смоляных кислот",
        "Жирных кислотсоли калия, кальция, натрия", "Моно- и диглицериды жирных кислот",
        "Различные эфиры моно- и диглицеридов жирных кислот", "Эфиры глицерина, диацетилвинной и жирных кислот",
        "Эфиры сахарозы и жирных кислот", "Сахароглицериды", "Эфиры полиглицеридов и жирных кислот",
        "Полиглицерин, полирицинолеаты", "Пропан-1,2-диоловые эфиры жирных кислот",
        "Эфиры лактилированных жирных кислот глицерина и пропиленгликоля",
        "Термически окисленное соевое и бобовое масло с моно- и диглицеридами жирных кислот",
        "Стеароил-2-лактилат натрия", "Стеароил-2-лактилат кальция", "Стеарилтартрат",
        "Сорбитан моностеарат", "Сорбитан тристеарат", "Сорбитан монолаурат",
        "Сорбитан моноолеат", "Сорбитан монопальмитат", "Костный фосфат",
        "Стеариновая кислота", "Стеарат магния", "Инозиновая кислота",
        "Инозинат натрия двузамещенный", "Инозинат калия двузамещенный",
        "5-инозинат кальция", "5-рибонуклеотиды кальция", "5-рибонуклеотиды натрия двузамещенные",
        "Глицин и его натриевые соли", "Шеллак", "L-цистеин", "Искусственные красители",
        "Искусственные ароматизаторы", "Бета-каротин", "Бутилоксианизол или бутилгидрокситолуол",
        "Липолизированный молочный жир", "Сухие кисломолочные продукты",
        "Стеарат кальция", "Стеароил-лактилат кальция",
        'E107', 'E133', 'E154', 'E495', 'E920', 'E100', 'E101', 'E102', 'E104',
        'E110', 'E122', 'E123', 'E124', 'E127', 'E128', 'E131', 'E132', 'E140',
        'E141', 'E142', 'E151', 'E153', 'E160c', 'E160f', 'E161c', 'E161f', 'E163',
        'E160a', 'E160d', 'E161a', 'E161d', 'E161g', 'E170', 'E160e', 'E161b',
        'E161e', 'E162', 'E180', 'E213', 'E214', 'E215', 'E216', 'E217', 'E218',
        'E219', 'E227', 'E230', 'E231', 'E232', 'E233', 'E270', 'E282', 'E304',
        'E306', 'E308', 'E309', 'E302', 'E307', 'E311', 'E312', 'E320', 'E321',
        'E325', 'E326', 'E327', 'E333', 'E334', 'E335', 'E336', 'E337', 'E341',
        'E322', 'E422', 'E470', 'E471', 'E472', 'E473', 'E474', 'E475', 'E476',
        'E477', 'E478', 'E481', 'E482', 'E483', 'E491', 'E492', 'E493', 'E494',
        'E542', 'E544', 'E556', 'E620', 'E621', 'E622', 'E623', 'E627', 'E631',
        'E635', 'E904'
    },
    "general_suspected": {
        "Ароматизаторы", "Консерванты", "Красители", "Стабилизаторы",
        "Эмульгаторы", "Регуляторы кислотности", "Усилитель вкуса и аромата"
    }
}

HARAM_INGREDIENTS = ALL_INGREDIENTS["haram"]
SUSPECTED_INGREDIENTS = ALL_INGREDIENTS["suspected"]
GENERAL_SUSPECTED_INGREDIENTS = ALL_INGREDIENTS["general_suspected"]


def check_halal_status(ingredients, threshold=80):
    

    found_haram = set()
    found_suspected = set()
    found_general_suspected = set()

    def matches_exact(element, reference_list):
        """Check for exact matches (case-insensitive)."""
        return element.lower() in (item.lower() for item in reference_list)

    def matches_fuzzy(element, reference_list):
        """Check for fuzzy matches only if the term is longer (more specific)."""
        element_lower = element.lower()
        for ref in reference_list:
            ref_lower = ref.lower()
            if len(element_lower.split()) > 1 and fuzz.partial_ratio(element_lower, ref_lower) >= threshold:
                return ref  # Return the closest match
        return None

    for ingredient in ingredients:
        words = ingredient.split()
        
        #  Step 1: If it's a general term (one word), mark it as "Suspicious"
        if len(words) == 1 and matches_exact(ingredient, GENERAL_SUSPECTED_INGREDIENTS):
            print(f"⚠️ {ingredient} - ОБЩЕЕ ПОДОЗРЕНИЕ")
            found_general_suspected.add(ingredient)
            continue  # Skip further checks

        #  Step 2: If it contains multiple words, check for haram ingredients **only if both words are present**
        if len(words) > 1:
            for haram_item in HARAM_INGREDIENTS:
                haram_words = haram_item.split()
                if len(haram_words) > 1 and all(word in words for word in haram_words):
                    print(f"❌ {ingredient} - ХАРАМ (Matched: {haram_item})")
                    found_haram.add(haram_item)
                    continue  # Skip further checks

        #  Step 3: Use fuzzy matching only for long specific terms
        match_haram = matches_fuzzy(ingredient, HARAM_INGREDIENTS)
        match_suspected = matches_fuzzy(ingredient, SUSPECTED_INGREDIENTS)
        match_general_suspected = matches_fuzzy(ingredient, GENERAL_SUSPECTED_INGREDIENTS)

        if match_haram:
            print(f"❌ {ingredient} - ХАРАМ (Matched: {match_haram})")
            found_haram.add(match_haram)
        elif match_suspected:
            print(f"⚠️ {ingredient} - ПОДОЗРИТЕЛЬНО (Matched: {match_suspected})")
            found_suspected.add(match_suspected)
        elif match_general_suspected:
            print(f"⚠️ {ingredient} - ОБЩЕЕ ПОДОЗРЕНИЕ (Matched: {match_general_suspected})")
            found_general_suspected.add(match_general_suspected)

    #  Step 4: Determine the overall status
    if found_haram:
        return {"status": "haram", "found_ingredients": list(found_haram)}
    elif found_suspected or found_general_suspected:
        return {"status": "Подозрительно", "found_ingredients": list(found_suspected | found_general_suspected)}
    else:
        return {"status": "halal", "found_ingredients": []}