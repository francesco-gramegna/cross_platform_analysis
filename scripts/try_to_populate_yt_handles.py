from populator import NamePopulator
import utils

data = utils.load_csvs_to_dicts("cleaned_dataset/updated/*")

pop = NamePopulator(data, 3)

pop.process()

