"""
Скрипт для создания словаря замен терминов из мира Наруто
Генерирует вымышленные названия для персонажей, техник, деревень и других сущностей
"""

import json
import random
import string

def generate_fake_name(base_length=None):
    """Генерирует вымышленное имя"""
    if base_length is None:
        base_length = random.randint(5, 10)
    
    # Используем комбинацию согласных и гласных для более естественных имен
    consonants = 'bcdfghjklmnprstvwxyz'
    vowels = 'aeiou'
    
    name = ''
    for i in range(base_length):
        if i % 2 == 0:
            name += random.choice(consonants).upper() if i == 0 else random.choice(consonants)
        else:
            name += random.choice(vowels)
    
    return name

def generate_tech_name():
    """Генерирует название техники"""
    prefixes = ['Void', 'Shadow', 'Light', 'Dark', 'Crystal', 'Storm', 'Flame', 'Ice', 'Thunder', 'Wind']
    suffixes = ['Strike', 'Blade', 'Wave', 'Sphere', 'Beam', 'Rush', 'Burst', 'Edge', 'Core', 'Force']
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"

def generate_place_name():
    """Генерирует название места"""
    prefixes = ['Ver', 'Kor', 'Zar', 'Nex', 'Thal', 'Mor', 'Val', 'Eld']
    suffixes = ['gard', 'heim', 'vale', 'port', 'haven', 'keep', 'hold', 'gate']
    return f"{random.choice(prefixes)}{random.choice(suffixes)}"

# Словарь замен для мира Наруто
TERMS_MAP = {
    # Персонажи
    "Naruto Uzumaki": "Kael Vexaris",
    "Sasuke Uchiha": "Zephyr Darkwind",
    "Sakura Haruno": "Lyra Brightstone",
    "Kakashi Hatake": "Raven Shadowblade",
    "Itachi Uchiha": "Vex Nightshade",
    "Madara Uchiha": "Malakor Voidheart",
    "Obito Uchiha": "Orion Shadowweaver",
    "Hashirama Senju": "Haldor Stormborn",
    "Tobirama Senju": "Toren Frostweaver",
    "Hiruzen Sarutobi": "Haven Ironwill",
    "Minato Namikaze": "Miran Swiftblade",
    "Jiraiya": "Jaxon Wavecaller",
    "Tsunade": "Thalia Goldheart",
    "Orochimaru": "Oren Serpentfang",
    "Gaara": "Gareth Sandstorm",
    "Rock Lee": "Rex Ironfist",
    "Neji Hyuga": "Nolan Skysight",
    "Hinata Hyuga": "Helena Stargaze",
    "Shikamaru Nara": "Silas Shadowmind",
    "Choji Akimichi": "Corbin Boulderheart",
    "Ino Yamanaka": "Iris Mindweaver",
    
    # Кланы
    "Uchiha Clan": "Voidheart Clan",
    "Senju Clan": "Stormborn Clan",
    "Hyuga Clan": "Skysight Clan",
    "Uzumaki Clan": "Vexaris Clan",
    "Nara Clan": "Shadowmind Clan",
    "Akimichi Clan": "Boulderheart Clan",
    "Yamanaka Clan": "Mindweaver Clan",
    
    # Деревни
    "Konohagakure": "Verdantgate",
    "Sunagakure": "Sandhaven",
    "Kirigakure": "Mistport",
    "Kumogakure": "Cloudkeep",
    "Iwagakure": "Stonehold",
    "Konoha": "Verdantgate",
    "Sunagakure": "Sandhaven",
    "Kirigakure": "Mistport",
    "Kumogakure": "Cloudkeep",
    "Iwagakure": "Stonehold",
    
    # Техники
    "Rasengan": "Void Sphere",
    "Chidori": "Thunder Strike",
    "Shadow Clone Technique": "Phantom Duplication",
    "Sharingan": "Void Eye",
    "Rinnegan": "Eternal Gaze",
    "Byakugan": "Sky Vision",
    "Sage Mode": "Primal State",
    "Eight Gates": "Eight Seals",
    "Rasenshuriken": "Void Shuriken",
    "Amaterasu": "Void Flame",
    "Susanoo": "Void Guardian",
    "Kamui": "Void Shift",
    "Tsukuyomi": "Void Dream",
    "Izanagi": "Void Creation",
    "Izanami": "Void Cycle",
    
    # Хвостатые звери
    "Nine-Tailed Fox": "Nine-Tailed Void Fox",
    "Kurama": "Korvax",
    "One-Tailed Shukaku": "One-Tailed Sand Spirit",
    "Shukaku": "Shakor",
    "Eight-Tailed Gyuki": "Eight-Tailed Storm Ox",
    "Gyuki": "Gryx",
    
    # Организации
    "Akatsuki": "Void Order",
    "ANBU": "Shadow Guard",
    
    # События
    "Fourth Great Ninja War": "Fourth Great Shadow War",
    "Chunin Exams": "Apprentice Trials",
    "Great Ninja War": "Great Shadow War",
    
    # Другие термины
    "Ninja": "Shadow Warrior",
    "Shinobi": "Shadow Warrior",
    "Chakra": "Essence",
    "Jutsu": "Technique",
    "Genin": "Apprentice",
    "Chunin": "Warrior",
    "Jonin": "Master",
    "Kage": "Shadow Lord",
    "Hokage": "Shadow Lord of Verdantgate",
    "Kazekage": "Shadow Lord of Sandhaven",
    "Mizukage": "Shadow Lord of Mistport",
    "Raikage": "Shadow Lord of Cloudkeep",
    "Tsuchikage": "Shadow Lord of Stonehold",
}

def create_terms_map():
    """Создает и сохраняет словарь замен"""
    # Добавляем варианты написания
    extended_map = {}
    
    for original, replacement in TERMS_MAP.items():
        # Основная замена
        extended_map[original] = replacement
        
        # Варианты с разным регистром
        extended_map[original.lower()] = replacement.lower()
        extended_map[original.upper()] = replacement.upper()
        extended_map[original.title()] = replacement.title()
        
        # Если есть пробелы, добавляем варианты без пробелов
        if ' ' in original:
            extended_map[original.replace(' ', '')] = replacement.replace(' ', '')
            extended_map[original.replace(' ', '_')] = replacement.replace(' ', '_')
            extended_map[original.replace(' ', '-')] = replacement.replace(' ', '-')
    
    return extended_map

def main():
    print("Создание словаря замен терминов...")
    
    terms_map = create_terms_map()
    
    # Сохраняем основной словарь (только оригинальные пары)
    output_map = {k: v for k, v in TERMS_MAP.items()}
    
    with open('terms_map.json', 'w', encoding='utf-8') as f:
        json.dump(output_map, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Создан словарь с {len(output_map)} основными терминами")
    print(f"✓ Всего вариантов замен: {len(terms_map)}")
    print(f"✓ Сохранено в terms_map.json")
    
    # Выводим статистику
    characters = [k for k in output_map.keys() if any(char.isupper() and k[0].isupper() for char in k) and 'Clan' not in k and 'gakure' not in k and 'Village' not in k and not any(tech in k for tech in ['Rasengan', 'Chidori', 'Sharingan', 'Rinnegan', 'Byakugan', 'Sage', 'Gates', 'Amaterasu', 'Susanoo', 'Kamui', 'Tsukuyomi', 'Izanagi', 'Izanami'])]
    clans = [k for k in output_map.keys() if 'Clan' in k]
    villages = [k for k in output_map.keys() if 'gakure' in k or k in ['Konoha']]
    techniques = [k for k in output_map.keys() if k not in characters + clans + villages]
    
    categories = {
        'Персонажи': characters,
        'Кланы': clans,
        'Деревни': villages,
        'Техники': techniques,
    }
    
    print("\nСтатистика по категориям:")
    for category, terms in categories.items():
        if terms:
            print(f"  {category}: {len(terms)}")

if __name__ == "__main__":
    main()

