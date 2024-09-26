import json
import os
import shutil
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from decimal import Decimal
from PyPDF2 import PdfMerger
from fractions import Fraction
import jinja2
import requests
import argparse
import math
import re
import configparser


# DISPLAY ================================================================================
def convertDecimalToFractionString(decString):
    finalString = ""
    if decString:
        dec = Decimal(decString)
        whole = math.floor(dec)
        remainder = dec - whole

        if whole != 0:
            finalString += str(whole)

        if remainder:
            frac = Fraction(remainder).limit_denominator(10)
            fracString = " <sup>{}</sup>&frasl;<sub>{}</sub>".format(frac.numerator, frac.denominator)
        else:
            fracString = ""

        finalString += fracString
        finalString = finalString.strip().lstrip()
        return finalString
    else:
        return ""

def intToRoman(num):
    m = ["", "M", "MM", "MMM"]
    c = ["", "C", "CC", "CCC", "CD", "D", "DC", "DCC", "DCCC", "CM "]
    x = ["", "X", "XX", "XXX", "XL", "L", "LX", "LXX", "LXXX", "XC"]
    i = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]

    thousands = m[num // 1000]
    hundreds = c[(num % 1000) // 100]
    tens = x[(num % 100) // 10]
    ones = i[num % 10]

    return (thousands + hundreds + tens + ones)

def getIngredientNoteAppend(ingredient):
    note = ingredient["note"]
    if note == '' or note == 'None' or (ingredient["unit"] == None and ingredient["food"] == None):
        return ""
    elif note[0] == '(':
        return " "
    else:
        return ", "

def pluralizeString(stringToPluralize):
    stringPluralized = stringToPluralize
    if stringToPluralize[-1] in ['h', 's', 'o']:
        stringPluralized += "es"
    else:
        stringPluralized += "s"

    return stringPluralized

def pluralizeUnit(quantity, unit):
    if unit:
        if quantity and quantity > 1 and unit != None and unit["name"] != "":
            return pluralizeString(unit["name"])
        else:
            return unit["name"]
    else:
        return ""

def pluralizeIngredient(quantity, unit, ingredientName):
    if quantity and quantity > 1 and (unit is None or unit["name"] in ["", "None"]):
        return pluralizeString(ingredientName)
    else:
        return ingredientName

# ORGANIZATIONAL DATA ====================================================================
def generateCategoryCache():
    cache = {}
    for recipe in globalRecipeCache.get("items"):
        for category in globalRecipeCache.get("items")[recipe].get("recipeCategory"):
            cache[category.get("slug")] = category
    return cache

def generateTagCache():
    cache = {}
    for recipe in globalRecipeCache.get("items"):
        for tag in globalRecipeCache.get("items")[recipe].get("tags"):
            cache[tag.get("slug")] = tag
    return cache

def getTagName(tagSlug):
    return globalTagCache[tagSlug].get("name")

def getCategoryName(categorySlug):
    return globalCategoryCache[categorySlug].get("name")


# RECIPE DATA ============================================================================
def getRecipeData(recipeSlug):
    return globalRecipeCache.get("items")[recipeSlug]

def getRecipeName(recipeSlug):
    return globalRecipeCache.get("items")[recipeSlug]["name"]

def getRecipeNumber(recipeSlug):
    return globalRecipeCache.get("items")[recipeSlug]["number"]

def setRecipeNumber(recipeSlug, number):
    globalRecipeCache.get("items")[recipeSlug]["number"] = number
    return

def dumpGlobalRecipeData():
    recipeCacheFile = open("recipeCache.json", "w")
    recipeCacheFile.write(json.dumps(globalRecipeCache))
    recipeCacheFile.close()
    return

def dumpRecipeData(slug, data):
    file = open(slug+".json","w")
    file.write(json.dumps(data))
    file.close()
    return

def fetchRecipeData(recipeSlug):
    url = "{}/api/recipes/{}".format(MEALIE_URL,recipeSlug)
    response = requests.get(url, headers=authHeader)
    fullRecipeData = response.json()
    #dumpRecipeData(recipeSlug, fullRecipeData)
    fullRecipeData["imageUrl"] = "{}/api/media/recipes/{}/images/min-original.webp".format(MEALIE_URL,fullRecipeData.get("id"))
    return fullRecipeData

def fetchAllRecipesWithData():
    url = "{}/api/recipes?perPage=-1&loadFood=false".format(MEALIE_URL)
    response = requests.get(url, headers=authHeader)
    listData = response.json()
    dictConvert = {}
    for recipe in listData.get("items"):
        if not shouldRemoveTaggedRecipe(recipe) and recipeHasDesiredCategories(recipe):
            fullRecipeData = fetchRecipeData(recipe.get("slug"))
            dictConvert[fullRecipeData["slug"]] = fullRecipeData
    listData["items"] = dictConvert
    return listData


# FILTERING GLOBAL DATA =========================================================================
def shouldRemoveTaggedRecipe(recipeObject):
    if not args.removeTags:
        return False
    else:
        for recipeTag in recipeObject.get("tags"):
            if recipeTag.get("slug") in args.removeTags:
                return True 
    return False

def recipeHasCategory(recipeObject, category):
    for recipeCategory in recipeObject.get("recipeCategory"):
        if recipeCategory.get("slug") == category:
            return True
    return False

def recipeHasDesiredCategories(recipeObject):
    containsAtLeastOneCategory = False
    if not args.categories:
        return True # n/a
    else:
        for category in args.categories:
            if recipeHasCategory(recipeObject, category):
                containsAtLeastOneCategory = True
    return containsAtLeastOneCategory



# FILTERING ==============================================================================
def getRecipeSlugsWithTag(tagSlug):
    recipeSlugList = []
    for recipe in globalRecipeCache.get("items"):
        recipeObject = globalRecipeCache.get("items")[recipe]
        if recipeHasTag(recipeObject, tagSlug):
            recipeSlugList.append(recipeObject.get("slug"))
    return recipeSlugList

def getRecipeSlugsWithCategory(categorySlug):
    recipeSlugList = []
    for recipe in globalRecipeCache.get("items"):
        recipeObject = globalRecipeCache.get("items")[recipe]
        if recipeHasCategory(recipeObject, categorySlug):
            if args.tag:
                if recipeHasTag(recipeObject, args.tag):
                    recipeSlugList.append(recipeObject.get("slug"))
            else:
                recipeSlugList.append(recipeObject.get("slug"))
    return recipeSlugList

def getRecipeSlugsWithIngredient(ingredientName):
    recipeSlugList = []
    for recipe in globalRecipeCache.get("items"):
        recipeObject = globalRecipeCache.get("items")[recipe]
        if recipeHasIngredient(recipeObject, ingredientName):
            if args.tag:
                if recipeHasTag(recipeObject, args.tag):
                    recipeSlugList.append(recipeObject.get("slug"))
            else:
                recipeSlugList.append(recipeObject.get("slug"))
    return recipeSlugList

def recipeHasCategory(recipeObject, categorySlug):
    for category in recipeObject.get("recipeCategory"):
        if category.get("slug") == categorySlug:
            return True
    return False

def recipeHasTag(recipeObject, tagSlug):
    for tag in recipeObject.get("tags"):
        if tag.get("slug") == tagSlug:
            return True
    return False

def recipeHasIngredient(recipeObject, ingredientName):
    for ingredient in recipeObject.get("recipeIngredient"):
        if ingredient.get("food") and ingredient.get("food").get("name") == ingredientName:
            return True
    return False


# RENDERING HTML =========================================================================
def getRecipeAndRenderHTML(recipeSlug, number):
    recipeData = getRecipeData(recipeSlug)
    sourceHtml = recipeTemplate.render(data=recipeData,image=recipeData.get("imageUrl"), recipeNumber=number)
    return sourceHtml

def renderSectionHTML(categorySlug):
    title = getCategoryName(categorySlug)
    sourceHtml = sectionTemplate.render(title=title,
                                        manifest=globalCategoryManifest,
                                        category=categorySlug)
    return sourceHtml

def renderTitleHTML():
    title = TITLE if TITLE != None else "Cookbook"
    subtitle = SUBTITLE if SUBTITLE != None else ""
    sourceHtml = titleTemplate.render(title=title,subtitle=subtitle)
    return sourceHtml

def renderSpiceUsesHTML(page):
    return spiceUsesTemplate.render(pageNumber=page)

def renderSubstitutionsHTML(page):
    return substitutionsTemplate.render(pageNumber=page)

def renderUnitConversionsHTML(page):
    return unitConversionTemplate.render(pageNumber=page)

def renderSousVideHTML(page):
    return sousVideTemplate.render(pageNumber=page)

def renderDedicationHTML(dedicationText):
    sourceHtml = dedicationTemplate.render(dedication=dedicationText)
    return sourceHtml

def renderToCHTML():
    sourceHtml = tocTemplate.render(title="Contents", categoryManifest=globalCategoryManifest,staticPageCatalog=globalStaticCatalog)
    return sourceHtml

def renderIndexHTML():
    sortedManifestKeys = sorted(globalIndexCatalog)
    sourceHtml = indexTemplate.render(title="Index", 
                                        indexCatalog=globalIndexCatalog,
                                        tagManifest=globalTagManifest,
                                        ingredientManifest=globalIngredientManifest,
                                        sortedManifestKeys=sortedManifestKeys)
    return sourceHtml

def saveHtml(htmlContent, outputHTMLFilename):
    htmlFile = open(outputHTMLFilename, "w")
    htmlFile.write(htmlContent)
    htmlFile.close()
    return


# GENERATE PDF ===========================================================================
def convertHtmlToPdf(htmlFileName, stylesFilename, outputPDFFilename):
    font_config = FontConfiguration()
    htmlFile = open(htmlFileName, "r")
    html = HTML(string=htmlFile.read(),base_url='base_url')
    htmlFile.close()
    css = CSS(stylesFilename, font_config=font_config)
    html.write_pdf(outputPDFFilename, stylesheets=[css], font_config=font_config)
    return

def generateSectionHeaderPDF(category):
    renderedHTML = renderSectionHTML(category)
    if not os.path.exists("output/{}".format(category)):
        os.mkdir("output/{}".format(category))
    outputPDFFilename = "output//{}.pdf".format(category)
    outputHTMLFilename = "output//{}.html".format(category)
    stylesFilename = "templates//section_template.css"
    saveHtml(renderedHTML, outputHTMLFilename)
    convertHtmlToPdf(outputHTMLFilename, stylesFilename, outputPDFFilename)
    return

def generateTitlePDF():
    renderedHTML = renderTitleHTML()
    outputPDFFilename = "output//title.pdf"
    outputHTMLFilename = "output//title.html"
    stylesFilename = "templates//title_template.css"
    saveHtml(renderedHTML, outputHTMLFilename)
    convertHtmlToPdf(outputHTMLFilename, stylesFilename, outputPDFFilename)
    return

def generateSpiceUsesPDF(pageNumber):
    renderedHTML = renderSpiceUsesHTML(pageNumber)
    outputPDFFilename = "output//spice_uses.pdf"
    outputHTMLFilename = "output//spice_uses.html"
    stylesFilename = "templates//spice_uses_template.css"
    saveHtml(renderedHTML, outputHTMLFilename)
    convertHtmlToPdf(outputHTMLFilename, stylesFilename, outputPDFFilename)
    return

def generateSubstitutionsPDF(pageNumber):
    renderedHTML = renderSubstitutionsHTML(pageNumber)
    outputPDFFilename = "output//substitutions.pdf"
    outputHTMLFilename = "output//substitutions.html"
    stylesFilename = "templates//substitutions_template.css"
    saveHtml(renderedHTML, outputHTMLFilename)
    convertHtmlToPdf(outputHTMLFilename, stylesFilename, outputPDFFilename)
    return
    
def generateUnitConversionsPDF(pageNumber):
    renderedHTML = renderUnitConversionsHTML(pageNumber)
    outputPDFFilename = "output//unit_conversions.pdf"
    outputHTMLFilename = "output//unit_conversions.html"
    stylesFilename = "templates//unit_conversions_template.css"
    saveHtml(renderedHTML, outputHTMLFilename)
    convertHtmlToPdf(outputHTMLFilename, stylesFilename, outputPDFFilename)
    return

def generateSousVidePDF(pageNumber):
    renderedHTML = renderSousVideHTML(pageNumber)
    outputPDFFilename = "output//sous_vide.pdf"
    outputHTMLFilename = "output//sous_vide.html"
    stylesFilename = "templates//sous_vide_template.css"
    saveHtml(renderedHTML, outputHTMLFilename)
    convertHtmlToPdf(outputHTMLFilename, stylesFilename, outputPDFFilename)
    return

def generateDedicationPDF(dedicationText):
    renderedHTML = renderDedicationHTML(dedicationText)
    outputPDFFilename = "output//dedication.pdf"
    outputHTMLFilename = "output//dedication.html"
    stylesFilename = "templates//dedication_template.css"
    saveHtml(renderedHTML, outputHTMLFilename)
    convertHtmlToPdf(outputHTMLFilename, stylesFilename, outputPDFFilename)
    return

def generateToCPDF():
    renderedHTML = renderToCHTML()
    outputPDFFilename = "output//toc.pdf"
    outputHTMLFilename = "output//toc.html"
    stylesFilename = "templates//toc_template.css"
    saveHtml(renderedHTML, outputHTMLFilename)
    convertHtmlToPdf(outputHTMLFilename, stylesFilename, outputPDFFilename)
    return

def generateIndexPDF():
    renderedHTML = renderIndexHTML()
    outputPDFFilename = "output//index.pdf"
    outputHTMLFilename = "output//index.html"
    stylesFilename = "templates//index_template.css"
    saveHtml(renderedHTML, outputHTMLFilename)
    convertHtmlToPdf(outputHTMLFilename, stylesFilename, outputPDFFilename)
    return

def getRecipeAndConvertToPDF(recipeSlug, categorySlug, recipeNumber):
    renderedHTML = getRecipeAndRenderHTML(recipeSlug, recipeNumber)
    if not os.path.exists("output/{}".format(categorySlug)):
        os.mkdir("output/{}".format(categorySlug))
    outputPDFFilename = "output//{}//{}.pdf".format(categorySlug, recipeSlug)
    outputHTMLFilename = "output//{}//{}.html".format(categorySlug, recipeSlug)
    stylesFilename = "templates//recipe_page_template.css"
    saveHtml(renderedHTML, outputHTMLFilename)
    convertHtmlToPdf(outputHTMLFilename, stylesFilename, outputPDFFilename)
    return

def generateSingleRecipePage(recipeSlug):
    recipeData = fetchRecipeData(recipeSlug)
    renderedHTML = recipeTemplate.render(data=recipeData,image=recipeData.get("imageUrl"),recipeNumber=123)
    outputPDFFilename = "output//{}.pdf".format(recipeSlug)
    outputHTMLFilename = "output//{}.html".format(recipeSlug)
    stylesFilename = "templates//recipe_page_template.css"
    saveHtml(renderedHTML, outputHTMLFilename)
    convertHtmlToPdf(outputHTMLFilename, stylesFilename, outputPDFFilename)
    return


# COMBINING PDFs =========================================================================
def combinePDFs():
    #merger = PdfFileMerger()
    merger = PdfMerger()
    merger.append("output//title.pdf")
    if DEDICATION != None:
        merger.append("output//dedication.pdf")
    merger.append("output//toc.pdf")
    if args.static_pages:
        merger.append("output//spice_uses.pdf")
        merger.append("output//substitutions.pdf")
        merger.append("output//unit_conversions.pdf")
        merger.append("output//sous_vide.pdf")
    for categorySlug in globalCategoryManifest:
        print("Combining PDFs for category: {}".format(categorySlug))
        sectionFileName = "output//{}.pdf".format(categorySlug)
        merger.append(sectionFileName)
        for recipe in globalCategoryManifest[categorySlug]:
            recipeFileName = "output//{}//{}.pdf".format(categorySlug, recipe)
            merger.append(recipeFileName)
    merger.append("output//index.pdf")
        
    merger.write("recipe_book_preview.pdf")
    merger.close()


# FILE MANAGEMENT ========================================================================
def prepareOutputDir():
    if os.path.exists("output"):
        shutil.rmtree("output")
    os.mkdir("output")
    return


# MANIFEST MANAGEMENT ====================================================================
def buildCategoryManifest(categories):
    # Build list from categories
    recipeNumber = 1
    manifest = {}

    for categorySlug in categories:
        recipeSlugs = sorted(getRecipeSlugsWithCategory(categorySlug))
        if len(recipeSlugs) > 0:
            manifest[categorySlug] = []
        for recipeSlug in recipeSlugs:
            manifest[categorySlug].append(recipeSlug)
            setRecipeNumber(recipeSlug, recipeNumber)
            recipeNumber += 1
    return manifest

def recipeInCategoryManifest(recipeName):
    for categorySlug in globalCategoryManifest:
        for recipeSlug in globalCategoryManifest[categorySlug]:
            if recipeSlug == recipeName:
                return True
    return False

def buildIngredientManifest(foodList):
    manifest = {}
    for ingredient in foodList:
        recipeSlugs = sorted(getRecipeSlugsWithIngredient(ingredient))
        if MIN_RECIPES == 0 or len(recipeSlugs) >= MIN_RECIPES:
            if MAX_RECIPES == 0 or len(recipeSlugs) <= MAX_RECIPES:
                if len(recipeSlugs) > 0:
                    manifest[ingredient] = []
                for recipeSlug in recipeSlugs:
                    if recipeInCategoryManifest(recipeSlug):
                        manifest[ingredient].append(recipeSlug) 
    return manifest

def buildTagManifest():
    manifest = {}
    for tag in globalTagCache:
        if not args.tag or args.tag != tag:
            recipeSlugs = sorted(getRecipeSlugsWithTag(tag))
            if len(recipeSlugs) > 0:
                manifest[tag] = []
            for recipeSlug in recipeSlugs:
                if recipeInCategoryManifest(recipeSlug):
                    manifest[tag].append(recipeSlug)
    return manifest

def buildIndexCatalog():
    catalog = {}
    for categorySlug in globalCategoryManifest:
        for recipeSlug in globalCategoryManifest[categorySlug]:
            catalog[recipeSlug] = "r"

    for tag in globalTagManifest:
        for recipeSlug in globalTagManifest[tag]:
            if not args.indexIgnoreTags or tag not in args.indexIgnoreTags:
                catalog[tag] = "t"

    for ingredientName in globalIngredientManifest:
        for recipeSlug in globalIngredientManifest[ingredientName]:
            catalog[ingredientName] = "i"

    return catalog

def buildStaticPagesCatalog():
    catalog = {}
    catalog['Herb Uses'] = intToRoman(1)
    catalog['Substitutions'] = intToRoman(2)
    catalog['Unit Conversions'] = intToRoman(3)
    catalog['Sous Vide Times'] = intToRoman(4)

    return catalog

# INGREDIENT DUMP ========================================================================
def dumpIngredientList():
    foodDict = {}
    for recipe in globalRecipeCache.get("items"):
        for ingredient in globalRecipeCache.get("items")[recipe].get("recipeIngredient"):
            if ingredient.get("food"):
                foodDict[ingredient.get("food").get("name")] = ""
    with open("ingredientsForIndex.txt", "w") as file:
        for item in foodDict.keys():
            file.write(item + "\n")
    print("Ingredients dumped to file")
    return

def readFoodsFromFile(filePath):
    foodList = []
    with open(filePath) as f:
        for line in f:
            foodList.append(line.replace('\n',''))
    return foodList

def readDedicationFromFile(filePath):
    dedicationText = ""
    with open(filePath) as f:
        dedicationText = f.read()
    return dedicationText

# RECIPE POLISHING ========================================================================
# https://regex101.com

def findAndPrintOvenTempsInSteps():
    # °F
    print("\nChecking for Oven Temps...\n")
    regex = "(\d *(f|F)[^°F|\w])|(\d\.)|((f|F)ahrenheit)|((C|c)elsius)|((d|D)egree)"
    findAndPrintStringsInSteps(regex)
    return

def findAndPrintMeasurementsInSteps():
    print("\nChecking for Measurements...\n")
    regex = "(( |\d)(c|C)( |\W)|( |\d)(t|T)( |\W)|( |\d)(t|T)sp |( |\d)(t|T)bsp |( |\d)(m|M)in( |\.)|( |\d)(h|H)r( |\.)|(( |\d)(c|C)( |\W)|( |\d)(t|T)( |\W)|( |\d)(t|T)sp |( |\d)(t|T)bsp |( |\d)(m|M)in |(m|M)( |\W))(m|M)( |\W))|( \d *(in|In)( |\.))"
    findAndPrintStringsInSteps(regex)
    return

def findAndPrintFractionsInSteps():
    # <sup>1</sup>&frasl;<sub>2</sub>
    print("\nChecking for fractions...\n")
    regex = "(\d *\/ *\d)"
    findAndPrintStringsInSteps(regex)
    return

def findAndPrintLinesNotEndingWithPeriod():
    print("\nChecking for lines not ending in period...\n")
    regex = "[^(\.|\!)]\Z"
    findAndPrintStringsInSteps(regex)
    return

def findAndPrintStringsInSteps(regex):
    for recipe in globalRecipeCache.get("items"):
        recipeObject = globalRecipeCache.get("items")[recipe]
        for step in recipeObject.get("recipeInstructions"):
            stepText = step.get("text")
            result = re.search(regex, stepText)
            if result != None:
                print(recipe + "  -  " + stepText)
    return

def findAndPrintPosessiveTitles():
    print("\nChecking for posessive titles...\n")
    regex = "'"
    findAndPrintLinesInTitle(regex)
    return

def findAndPrintLinesInTitle(regex):
    for recipe in globalRecipeCache.get("items"):
        recipeTitle = globalRecipeCache.get("items")[recipe].get("name")
        result = re.search(regex, recipeTitle)
        if result != None:
                print(recipe + "  -  " + recipeTitle)
    return

# CONFIG LOADING =========================================================================

def get_config_value(section, option):
    if not global_config.has_option(section, option):
        print("Missing config value: {}.{}".format(section, option))
        return None

    return global_config[section][option]

# MAIN ===================================================================================
if __name__ == "__main__":

    # Config
    global_config = configparser.ConfigParser()
    global_config.read('config.ini')
    TITLE = get_config_value('cookbook', 'title')
    SUBTITLE = get_config_value('cookbook', 'sub_title')
    DEDICATION = get_config_value('cookbook', 'dedication')
    MIN_RECIPES = int(get_config_value('index_page', 'min_recipes'))
    MAX_RECIPES = int(get_config_value('index_page', 'max_recipes'))
    MEALIE_URL = get_config_value('mealie_instance', 'url')
    API_TOKEN = get_config_value('mealie_instance', 'api_token')

    # API Auth
    authHeader={
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(API_TOKEN)
    }

    # Argument Parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tag")
    parser.add_argument("-c", "--categories", nargs="+")
    parser.add_argument("-i", "--indexIgnoreTags", nargs="+")
    parser.add_argument("--removeTags", nargs="+")
    parser.add_argument("-f", "--foods", nargs="+")
    parser.add_argument("--foodFile", nargs='?', const=True, default=False, type=bool)
    parser.add_argument("-r", "--recipe")
    parser.add_argument("--ingredientDump", nargs='?', const=True, default=False, type=bool)
    parser.add_argument("--static_pages", action='store_true')
    parser.add_argument("--just_static_pages", action='store_true')
    parser.add_argument("--find_step_issues", action='store_true')
    parser.add_argument("--find_title_issues",action='store_true')
    args = parser.parse_args()

    # Global data objects
    globalRecipeCache = {}
    globalCategoryCache = {}
    globalTagCache = {}
    globalCategoryManifest = {}
    globalIngredientManifest = {}
    globalTagManifest = {}
    globalIndexCatalog = {}
    globalStaticCatalog = {}
    

    # Templates
    templateLoader = jinja2.FileSystemLoader(searchpath="./templates")
    templateEnv = jinja2.Environment(loader=templateLoader)
    recipeTemplate = templateEnv.get_template("recipe_page_template.html")
    recipeTemplate.globals['convertDecimalToFractionString'] = convertDecimalToFractionString
    recipeTemplate.globals['getIngredientNoteAppend'] = getIngredientNoteAppend
    recipeTemplate.globals['pluralizeUnit'] = pluralizeUnit
    recipeTemplate.globals['pluralizeIngredient'] = pluralizeIngredient
    sectionTemplate = templateEnv.get_template("section_template.html")
    sectionTemplate.globals['getRecipeName'] = getRecipeName
    sectionTemplate.globals['getRecipeNumber'] = getRecipeNumber
    titleTemplate = templateEnv.get_template("title_template.html")
    tocTemplate = templateEnv.get_template("toc_template.html")
    tocTemplate.globals['getRecipeName'] = getRecipeName
    tocTemplate.globals['getCategoryName'] = getCategoryName
    tocTemplate.globals['getRecipeNumber'] = getRecipeNumber
    indexTemplate = templateEnv.get_template("index_template.html")
    indexTemplate.globals['getRecipeName'] = getRecipeName
    indexTemplate.globals['getRecipeNumber'] = getRecipeNumber
    dedicationTemplate = templateEnv.get_template("dedication_template.html")
    spiceUsesTemplate = templateEnv.get_template("spice_uses_template.html")
    substitutionsTemplate = templateEnv.get_template("substitutions_template.html")
    unitConversionTemplate = templateEnv.get_template("unit_conversions_template.html")
    sousVideTemplate = templateEnv.get_template("sous_vide_template.html")


    prepareOutputDir()

    if args.recipe:
        generateSingleRecipePage(args.recipe)
    elif args.ingredientDump:
        print("Building caches...")
        globalRecipeCache = fetchAllRecipesWithData()
        dumpIngredientList()
    elif args.find_step_issues:
        print("Building caches...")
        globalRecipeCache = fetchAllRecipesWithData()
        findAndPrintOvenTempsInSteps()
        findAndPrintMeasurementsInSteps()
        findAndPrintLinesNotEndingWithPeriod()
        findAndPrintFractionsInSteps()
    elif args.find_title_issues:
        print("Building caches...")
        globalRecipeCache = fetchAllRecipesWithData()
        findAndPrintPosessiveTitles()
    elif args.just_static_pages:
        print("generating static pages")
        generateSpiceUsesPDF(intToRoman(1))
        generateSubstitutionsPDF(intToRoman(2))
        generateUnitConversionsPDF(intToRoman(3))
        generateSousVidePDF(intToRoman(4))
    elif args.categories:

        print("Building caches...")
        globalRecipeCache = fetchAllRecipesWithData()
        dumpGlobalRecipeData()
        globalCategoryCache = generateCategoryCache()
        globalTagCache = generateTagCache()

        globalCategoryManifest = buildCategoryManifest(args.categories)
        globalTagManifest = buildTagManifest()

        globalStaticCatalog = buildStaticPagesCatalog()

        generateTitlePDF()

        if args.static_pages:
            generateSpiceUsesPDF(globalStaticCatalog['Herb Uses'])
            generateSubstitutionsPDF(globalStaticCatalog['Substitutions'])
            generateUnitConversionsPDF(globalStaticCatalog['Unit Conversions'])
            generateSousVidePDF(globalStaticCatalog['Sous Vide Times'])

        if DEDICATION != None and DEDICATION != "":
            generateDedicationPDF(DEDICATION)

        generateToCPDF()
        for categorySlug in globalCategoryManifest:
            print("Category: " + categorySlug)
            generateSectionHeaderPDF(categorySlug)
            for recipe in globalCategoryManifest[categorySlug]:
                print("  Recipe: " + recipe)
                getRecipeAndConvertToPDF(recipe, categorySlug, getRecipeNumber(recipe))
        
        if args.foods:
            globalIngredientManifest = buildIngredientManifest(args.foods)
        elif args.foodFile:
            globalIngredientManifest = buildIngredientManifest(readFoodsFromFile("ingredientsForIndex.txt"))
        else:
            globalIngredientManifest = buildIngredientManifest([])

        print("Building Index")
        globalIndexCatalog = buildIndexCatalog()
        generateIndexPDF()
        
        combinePDFs()
    