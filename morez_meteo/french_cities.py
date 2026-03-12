"""
Villes françaises métropolitaines de référence pour le classement pluviométrique.
Sélection représentative couvrant toutes les régions + villes réputées pluvieuses.
"""

# (nom, lat, lon)
FRENCH_CITIES = [
    # Nord / Bretagne / Normandie (réputées pluvieuses)
    ("Brest",          48.3904,  -4.4861),
    ("Cherbourg",      49.6333,  -1.6167),
    ("Rennes",         48.1173,  -1.6778),
    ("Nantes",         47.2184,  -1.5536),
    ("Rouen",          49.4432,   1.0993),
    ("Lille",          50.6292,   3.0573),
    # Massif Central / Alpes / Pyrénées (zones de montagne pluvieuses)
    ("Grenoble",       45.1885,   5.7245),
    ("Chambéry",       45.5646,   5.9178),
    ("Pau",            43.2951,  -0.3708),
    ("Tarbes",         43.2328,   0.0781),
    ("Aurillac",       44.9256,   2.4421),
    ("Le Puy-en-Velay",45.0430,   3.8819),
    ("Clermont-Ferrand",45.7797,   3.0863),
    # Alsace / Vosges
    ("Strasbourg",     48.5734,   7.7521),
    ("Épinal",         48.1741,   6.4508),
    # Jura / Est
    ("Besançon",       47.2378,   6.0241),
    ("Lons-le-Saunier",46.6751,   5.5561),
    ("Saint-Claude",   46.3869,   5.8653),
    # Côte Atlantique
    ("La Rochelle",    46.1603,  -1.1511),
    ("Bordeaux",       44.8378,  -0.5792),
    # Méditerranée (moins pluvieux pour contraste)
    ("Marseille",      43.2965,   5.3698),
    ("Nice",           43.7102,   7.2620),
    ("Montpellier",    43.6119,   3.8772),
    # Paris / Centre
    ("Paris",          48.8566,   2.3522),
    ("Lyon",           45.7640,   4.8357),
]
