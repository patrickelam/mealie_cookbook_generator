# Mealie Cookbook Generator

I started playing with [Mealie](https://github.com/mealie-recipes/mealie) a while back and have found it to be a great tool. I have since digitized all of our family recipes and wanted a way to share those back with my family in a consistent format (no more magazine clippings and notecards with unreadable handwriting). 

This is a *very* basic script to generate a pdf using data from the Mealie API and isn't supposed to be production level code by any means; however, I was happy with the generated output, so figured if someone else could get value from my work, I'd love to be able to share it. "Someday" I'll modularize it.

An [example_output.pdf](./example_output.pdf) is included to demonstrate the scripts capabilities.


# Structure

The script pulls html and css from the `templates` directory, then injects data from the Mealie API to create recipe pages. These HTML pages are then rendered into individual PDF files. It also uses the API data to generate dynamic table of content pages, several hard-coded static reference pages, and an index section to help you find the recipe you're looking for quickly by listing all recipes by name, all recipes by common ingredients, and all recipes by tag. It finally combines all of the pages together to form the final book.


## Output

The script dumps the intermediate HTML files, as well as the rendered PDF files into the `output/` directory. The static pages and the meta pages are at the root directory, and then each category has a subdirectory. The final output of all combined pages written to the top level of the project.


# Usage

## Setup

This script is opinionated in how it assumes you have Mealie set up. First, it assumes that you have recipes divided into categories (with each recipe only belonging to a single category). It also assumes that you have standardized units and ingredients. The use of tags in Mealie is optional, and they can be used to group like things in the index file at the end of the book.

As of this writing, this works against the 1.0.0beta-5 version of Mealie.


## Python

This script is a python3 script and works with python 3.10.6. If you don't already use it, I recommend [pyenv](https://github.com/pyenv/pyenv) to manage python versions. Install the required packages with ```pip3 install -r requirements.txt```.


## Configuration File

The repo contains a file named `example_config.ini`. You'll need to copy or rename this file to a file named `config.ini` and then fill out fields.


### Cookbook Config

`title` and `sub_title` are the title and subtitle for the cookbook's title page. Title will default to "Cookbook". Subtitle will default to be empty.

If a line is given to the `dedication` field, this line will be generated by itself on a dedication page just after the title page.


### Mealie Instance Config

The `url` should be the URL of your Mealie instance, including the protocol (https://).

The script requires an API token to authenticate against the Mealie API. You can generate an API token from the `user/profile/api-tokens` page of your Mealie instance and store in the `api_token` field.


### Index Page Config

The index page groups recipes by name, ingredient, and tag. To prevent a whole section for every single ingredient - only common ones, the script can filter the ingredients used to create sections with the `min_recipes` and `max_recipes` options. These will specify the minimum and maximum number of recipes that contain a specific ingredient that will be required to create a section in the index. For example, you might not want an index section for salt, because most recipes have it. And you might not want an index section for walnuts if only one of your recipes has walnuts. You can set either of these values to 0 to remove the constraint.


## Commands

Run the generator script with python3:

```
python3 ./pdf_generator.py <arguments>
```


### Arguments

#### Tag

The `--tag` or `-t` flag allows you to limit recipes generated by passing in tags that the recipes must have to be included in the cookbook. If you don't pass in tag, recipes will not be filtered by tag. 

```
--tag moms_recipie recipes_i_actually_like
```


#### Categories

The `--categories` or `-c` flag specifies the categories of recipes that should be included in the cookbook AND specifies what order they should appear in. 
```
--categories breakfast lunch dinner dessert
```

Or, if you've got your priorities in order
```
-c dessert breakfast lunch
```

Or, if you're a hobbit
```
-c breakfast second_breakfast elevenses luncheon afternoon_tea dinner supper
```


#### Index Ignore Tags

The `--indexIgnoreTags` or `-i` flag specifies tags that you would not like to be included in the index page. I have a tag for "proof-reading needed" - I want that on the site for following up on recipes, but I don't want it to show up in the index page.

```
-i mom_hates
```


#### Remove Tags

The `--removeTags` flag will not generate recipes that have the given tag. If you want to tag recipes that aren't ready for prime-time, or are from the other side of the family.

```
--removeTags still_needs_proofing wifes_family
```


#### Static Pages

Add the `--static_pages` flag if you want to include the static content pages in the cookbook. These pages are hardcoded reference pages and are defined in the templates directory.


#### Foods

The `--foods` flag allows you to specify manually the ingredients that you want in the index. These will still be subject to minimum and maximum recipes as defined above.

```
--foods chickpeas
```


#### Food File

The `--foodFile` flag allows you to specify a file with the same purpose as the `--foods` flag. 

```
--foodFile ingredientsForIndex.txt
```

Where `ingredientsForIndex.txt` is

```
mustard
pizza crust
buffalo sauce
apple
...
```

*If neither `--foods` nor `--foodFile` are given, the index page will not have entries for ingredients.*


#### Ingredient Dump

The `--ingredientDump` flag will create a text file named `ingredientsForIndex.txt` with every single ingredient in the recipe list. You then can manually curate the contents to curate the index page sections.


#### Recipe Data Polishing

The `--find_title_issues` and `--find_step_issues` flags are standalone utilities that check your mealie data for inconsistencies that look bad in a final cookbook.

`--find_title_issues` checks for an apostrophe in recipe titles. I want Grandma's Muffins recipe to show up under M, not G, so I use this to find any instances of so-and-so's recipe and then add that information to the recipe description and change the title.

`--find_step_issues` checks for a number of things. It looks for steps that contain unspecific oven temperatures (I like using °F for consistency). It looks for variations in measurement shorthand (T, Tbsp, etc). It looks for fractions in steps that I like to change to use `<sup>1</sup>&frasl;<sub>2</sub>`. Finally, it checks for steps that don't end in a period.


## Example Usage

1) Organize the recipes in your Mealie instance.
2) Create the config file, and fill out the desired info.
```
mv config_example.ini config.ini
```
3) Get API token and save it to the config file.
4) Find and fix issues with Mealie recipes.
```
python3 ./pdf_generator.py --find_title_issues
python3 ./pdf_generator.py --find_step_issues
```
5) Dump ingredients to file and prune. (optional, but recommended)
```
python3 ./pdf_generator.py --ingredientDump
```
6) Build and run the command to build the book with all the options you want.
```
python3 ./pdf_generator.py -c breakfast side quick-bread soup dinner cookies ice-cream dessert sauce seasoning -i proofing-needed --removeTags aunt_barbs --static_pages --foodFile
```

The [example_output.pdf](./example_output.pdf) was generated using the following command:
```
python3 ./pdf_generator.py -c quick-bread --static_pages --removeTags <tags I don't want generated> -i <tags I don't want sections in the index>
```
Note, on the example index page, `Pumpkin` is a tag that I use to tie together all recipies with pumpkin. (I do the same with Chicken to tie together all the different `chicken thighs`, `chicken breast`, etc). Also note the generation of the Cinnamon category because two (the default minimum number) recipes contain cinnamon.


## Docker Alternative

If you have docker installed and don't want to fuss with setting up a python environment, you can build the docker image with
```
docker build --no-cache -t cookbook_generator .
```

And then run the python script in the docker image passing all the standard arguments. This command maps the working directory to the `/usr/src/app` directory, and thus will utilize any changes you make to the script or templates.
```
docker run --rm -it -v $(pwd):/usr/src/app cookbook_generator python ./pdf_generator.py -c quick-bread --foodFile
```


# Customization

The html template and css files are available in the `templates` directory and can be modified before running the script.