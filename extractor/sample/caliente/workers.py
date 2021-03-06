import json
import datetime
from multiprocessing import get_logger

from extractor.sample.common.model import GameMetadata
from pythontools.workermanager.workers import TimedWorker
from pythontools.messaging.rabbitmq import Producer, Consumer

class CalienteFetcher:
    PARSER = "parser"
    CORRECT_SCORE_GAME_CONTAINER_TYPE = "correct_score_game_container_type"
    CORRECT_SCORE_GAME_CONTAINER_TARGET = "correct_score_game_container_target"
    ODDS_CONTAINER_TYPE = "odds_container_type"
    ODDS_CONTAINER_TARGET = "odds_container_target"
    ODD_LABEL_TARGET = "odd_label_target"
    ODD_PRICE_US_CONTAINER_TYPE = "odd_price_us_container_type"
    ODD_PRICE_US_TARGET_CLASS = "odd_price_us_target_class"
    ODD_PRICE_FRAC_CONTAINER_TYPE = "odd_price_frac_container_type"
    ODD_PRICE_FRAC_TARGET_CLASS = "odd_price_frac_target_class"
    ODD_PRICE_DEC_CONTAINER_TYPE = "odd_price_dec_container_type"
    ODD_PRICE_DEC_TARGET_CLASS = "odd_price_dec_target_class"
    GAME_TYPE = "game_type"

    def __init__(self, config, http_helper, html_helper):
        """
        Initialize fetcher's instance.
        """
        self.name = CalienteFetcher.__name__
        self.http_helper = http_helper
        self.html_helper = html_helper
        self.logger = get_logger()
        self.load_config(config)

    def load_config(self, config):
        try:
            self.logger.info(f"intializing {CalienteFetcher.__name__} with {config}")
            self.parser = config[self.PARSER]
            self.correct_score_game_container_type = config[self.CORRECT_SCORE_GAME_CONTAINER_TYPE]
            self.correct_score_game_container_target = config[self.CORRECT_SCORE_GAME_CONTAINER_TARGET]
            self.odds_container_type = config[self.ODDS_CONTAINER_TYPE]
            self.odds_container_target = config[self.ODDS_CONTAINER_TARGET]
            self.odd_label_target = config[self.ODD_LABEL_TARGET]
            self.odd_price_us_container_type = config[self.ODD_PRICE_US_CONTAINER_TYPE]
            self.odd_price_us_target_class = config[self.ODD_PRICE_US_TARGET_CLASS]
            self.odd_price_frac_container_type = config[self.ODD_PRICE_FRAC_CONTAINER_TYPE]
            self.odd_price_frac_target_class = config[self.ODD_PRICE_FRAC_TARGET_CLASS]
            self.odd_price_dec_container_type = config[self.ODD_PRICE_DEC_CONTAINER_TYPE]
            self.odd_price_dec_target_class = config[self.ODD_PRICE_DEC_TARGET_CLASS]
            self.game_type = config[self.GAME_TYPE]
        except Exception as error:
            self.logger.error(f"invalid configuration for {CalienteFetcher.__name__} class")
            self.logger.error(error)
            raise error

    def fetch(self, url):
        """
        This method retrieves the content from a given url and returns
        the result from parse_results method.
        """
        try:
            self.logger.info(f"{self.name} - fetching odds page from {url}")
            odds_page = self.http_helper.get(url).text
        except Exception as error:
            self.logger.error(f"problems found while trying to get the data from {url} ... waiting for next attempt")
            self.logger.error(error)
            return None

        return self.parse_results(url, odds_page)
        

    def parse_results(self, url, odds_page):
        """
        This method creates a beautifulsoup object to parse the content received as argument
        and extracts the odds for a specific type of bet. It returns a Game object, which
        includes the list of odds found and related metadata. It returns None if there is an 
        error while trying to extract the data from the beautifulsoup object.
        """
        try:
            self.logger.info(f"{self.name} - parsing results")
            soup = self.html_helper.create_html_object(odds_page, self.parser)
            correct_score_table = soup.find(self.correct_score_game_container_type, self.correct_score_game_container_target)
            odds_container = correct_score_table.find_all(self.odds_container_type, self.odds_container_target)
            odd_metadata_list = []
            for odd in odds_container:
                odd_metadata = self.extract_odd_metadata(odd)
                odd_metadata_list.append(odd_metadata)
            return GameMetadata(url, self.game_type, odd_metadata_list, datetime.datetime.utcnow())
        except Exception as error:
            self.logger.error(f"{self.name} error found while trying to extract the data from the html tree {error}")    
            return None
    
    def extract_odd_metadata(self, odd_html_element):
        label = odd_html_element[self.odd_label_target]
        price_frac = odd_html_element.find(self.odd_price_frac_container_type, self.odd_price_frac_target_class).text
        price_dec = odd_html_element.find(self.odd_price_dec_container_type, self.odd_price_dec_target_class).text
        price_us = odd_html_element.find(self.odd_price_us_container_type, self.odd_price_us_target_class).text

        return [label, price_frac, price_dec, price_us]

class CalienteOddsProducer(Producer):
    def __init__(self, config):
        """
        Initialize odds producer.
        """
        super().__init__(config)
        self.logger = get_logger()
        self.logger.info(f"initializing {CalienteOddsProducer.__name__} with {config}")

    def send_odds(self, odds):
        """
        This method serializes the odds and calls produce method, 
        which is inherited from base Producer class,
        and passes the serialized odds as argument.
        """
        self.logger.info(f"serializing {odds} to json format")
        serialized_product = json.dumps(odds.__dict__, default=str)
        return self.produce(serialized_product)

class CalienteSeeder(TimedWorker):
    NEW = "new"
    FETCHING_LEAGUES = "fetching_leagues"
    FETCHING_GAMES = "fetching_games"
    READY = "ready"
    WAIT_TIME = "wait_time"
    BASE_HREF = "base_href"
    PRODUCER_CONFIG = "producer_config"
    LEAGUES_PATH = "leagues_path"
    HTML_PARSER = "html_parser"
    LEAGUES_CONTAINER_TYPE = "leagues_container_type"
    LEAGUES_CONTAINER_TARGET = "leagues_container_target"
    LEAGUE_URL_TYPE = "league_url_type"
    LEAGUE_URL_TARGET = "league_url_target"
    GAMES_CONTAINER_TYPE = "games_container_type"
    GAMES_CONTAINER_TARGET = "games_container_target"
    ODDS_CONTAINER_TARGET = "odds_container_target"
    ODDS_CONTAINER_TYPE = "odds_container_type"
    ODDS_LINK_TARGET = "odds_link_target"
    TARGET_LEAGUES = "target_leagues"
    URL_DELIMITER = "url_delimiter"
    TARGET_GAMES = "target_games"

    def __init__(self, config, cache_client, url_producer, http_helper, html_helper):
        """
        Initialize seeder instance.
        """
        super().__init__(config[self.WAIT_TIME])
        self.name = CalienteSeeder.__name__
        self.logger = get_logger()
        self.load_config(config)
        self.cache = cache_client
        self.message_producer = url_producer
        self.http_helper = http_helper
        self.html_helper = html_helper
        self.cache.create_worker_state(self.name, self.NEW)

    def load_config(self, config):
        try:
            self.logger.info(f"intializing {self.name} with {config}")
            self.base_href = config[self.BASE_HREF]
            self.leagues_url = f"{self.base_href}{config[self.LEAGUES_PATH]}"
            self.leagues_container_type = config[self.LEAGUES_CONTAINER_TYPE]
            self.leagues_container_target = config[self.LEAGUES_CONTAINER_TARGET]
            self.league_url_type = config[self.LEAGUE_URL_TYPE]
            self.league_url_target = config[self.LEAGUE_URL_TARGET]
            self.games_container_type = config[self.GAMES_CONTAINER_TYPE]
            self.games_container_target = config[self.GAMES_CONTAINER_TARGET]
            self.odds_container_type = config[self.ODDS_CONTAINER_TYPE]
            self.odds_container_target = config[self.ODDS_CONTAINER_TARGET]
            self.odds_link_target = config[self.ODDS_LINK_TARGET]
            self.html_parser = config[self.HTML_PARSER]
            # convert target list to set to perform O(1) access
            self.target_leagues = {*config[self.TARGET_LEAGUES]}
            self.url_delimiter = config[self.URL_DELIMITER]
            # convert target list to set to perform O(1) access
            self.target_games = {*config[self.TARGET_GAMES]}
        except Exception as error:
            self.logger.error(f"invalid configuration for {self.name}")
            self.logger.error(error)
            raise error


    def do_work(self):
        """
        This method manages the actions that the seeder needs to perform
        depending on the current seeder's state.
        """
        self.current_state = self.get_state()
        self.logger.info(f"{self.name} - {self.current_state}")
        if self.current_state == self.NEW:
            self.update_state(self.FETCHING_LEAGUES)
            self.get_leagues()
        elif self.current_state == self.FETCHING_LEAGUES:
            self.get_leagues()
        elif self.current_state == self.FETCHING_GAMES:
            if self.cache.get_pending_leagues() == 0:
                self.set_seeder_ready()
            else:
                self.get_games()
        elif self.current_state== self.READY:
            self.send_odds_link()

    def get_state(self):
        """
        Retrieves the seeder's state from the cache server.
        """ 
        state = self.cache.get_worker_state(self.name)
        if state == None:
            self.update_state(self.NEW)
        else:
            return state
        
        return self.cache.get_worker_state(self.name)

    def update_state(self, new_state):
        """
        Tells the cache client to update the current seeder's state.
        """
        self.cache.update_worker_state(self.name, new_state)
        self.current_state = self.cache.get_worker_state(self.name)

    def set_seeder_ready(self):
        """
        Tells the cache client to set the current seeder's state as 'ready'.
        """
        self.logger.info("seeder is ready, updating state...")
        self.update_state(self.READY)

    def get_leagues(self):
        """
        Retrieves the content of the page containing all the soccer leagues urls,
        then creates a beautifulsoup object to parse the result and extract the urls
        from the dom. Finally, tells the cache client to store the urls in the cache server
        and updates the current seeder's state.
        """
        self.logger.info(f"fetching leagues' URLs from {self.leagues_url}")
        try:
            football_leagues_page = self.http_helper.get(self.leagues_url).text
        except Exception as error:
            self.logger.error("problems found while making the http request... waiting for next attempt")
            self.logger.error(error)
            return

        try:
            soup = self.html_helper.create_html_object(football_leagues_page, self.html_parser)
            league_urls_container = soup.find(self.leagues_container_type, self.leagues_container_target)
            league_url_elements = league_urls_container.findAll(self.league_url_type)
            league_urls = []
            for league_url_element in league_url_elements:
                url = league_url_element[self.league_url_target]
                name = league_url_element.text
                league_urls.append(f"{self.base_href}{url}")
                self.logger.info(f"league name: {name} url: {url}")
        except Exception as error:
            self.logger.error(f"problems found while trying to extract the data from the dom... waiting for next attempt")
            self.logger.error(error)
            return

        self.logger.info(f"saving leagues' URLs")
        self.cache.save_leagues(self.filter_leagues(league_urls))
        self.update_state(self.FETCHING_GAMES)

    def filter_leagues(self, leagues):
        """
        Removes all leagues which aren't in target_list property
        """
        # avoid filter if target_leagues list is empty
        if len(self.target_leagues) == 0:
            return leagues

        self.logger.info("filtering target leagues")
        filtered_leagues = []
        for league in leagues:
            league_name = league.split(self.url_delimiter)[-1]
            if league_name in self.target_leagues:
                filtered_leagues.append(league)
        return filtered_leagues

    def filter_games(self, games):
        self.logger.info("filtering target games")
        # avoid filter if target_games list is empty
        if len(self.target_games) == 0:
            return games

        filtered_games = []
        for game in games:
            game_name = game.split(self.url_delimiter)[-1]
            if game_name in self.target_games:
                filtered_games.append(game)
        return filtered_games


    def get_games(self):
        """
        Retrieves the content of the page containing all the urls for all games
        in a given league, then creates a beautifulsoup object to parse the result and extract 
        from the dom the odds urls for each match. Finally, tells the cache client to store the 
        urls in the cache server and updates the current seeder's state.
        """
        url = self.cache.get_league()
        if url == None:
            self.logger.info("no game url available, updating seeder state and waiting for next attempt")
            self.set_seeder_ready()
            return

        try:
            league_games_page = self.http_helper.get(url).text
        except Exception as error:
            self.logger.error("problems found while making the http request... waiting for next attempt")
            self.logger.error(error)
            return

        try:
            self.logger.info(f"fetching odds for all games in league {url}")
            soup = self.html_helper.create_html_object(league_games_page, self.html_parser)
            games_table = soup.find_all(self.games_container_type, self.games_container_target)
            game_odds_list = []
            for match in games_table:
                full_bets_link = match.find(self.odds_container_type, self.odds_container_target)[self.odds_link_target]
                game_odds_list.append(f"{self.base_href}{full_bets_link}")
                self.logger.info(f"bets page link: {full_bets_link}")
        except Exception as error:
            self.logger.error(f"problems found while trying to extract the data from the dom object... waiting for next attempt")
            self.logger.error(error)
            return

        self.save_game_odds_urls(self.filter_games(game_odds_list))

    def save_game_odds_urls(self, game_odds_urls):
        self.logger.info("saving game odds' links in cache server")
        self.cache.save_games(game_odds_urls, datetime.datetime.utcnow())

    def get_game_url(self):
        self.logger.info("fetching game odds link from cache")
        return self.cache.get_oldest_game_url()

    def send_odds_link(self):
        """
        Retrieves an url from the cache and tells the producer to
        send the url to the corresponding queue so that it can be used
        by a fetcher instance.
        """
        match_url = self.get_game_url()
        return self.message_producer.send_url(match_url)

class CalienteUrlConsumer(Consumer):
    PRODUCER_CONFIG = "producer_config"
    FETCHER_CONFIG = "fetcher_config"
    DECODE_FORMAT = "decode_format"

    def __init__(self, config, odds_fetcher, odds_producer):
        """
        Initialize consumer instance.
        """
        super().__init__(CalienteUrlConsumer.__name__, config)
        self.logger = get_logger()
        self.load_config(config)
        self.odds_fetcher = odds_fetcher
        self.odds_producer = odds_producer

    def load_config(self, config):
        """
        Loads config values from dictionary
        """
        try:
            self.logger.info(f"initializing {CalienteUrlConsumer.__name__} with {config}")
            self.decode_format = config[self.DECODE_FORMAT]
        except Exception as error:
            self.logger.error(f"invalid configuration for {CalienteUrlConsumer.__name__}")
            self.logger.error(error)
            raise error

    def do_work(self, ch, method, properties, body):
        """
        This method is called when a message is received in the configured queue.
        It tells the fetcher to process the url and waits for the result. If the
        result isn't None, then it calls the send_odds method and passes the fetcher's
        result as argument.
        """
        self.logger.info(f"received new message with body => {body}")
        odds = self.get_odds_from_fetcher(body.decode(self.decode_format))

        if odds == None:
            self.logger.info(f"no odds found for {body}")
        else:            
            odds_sent = self.send_odds(odds)
            if odds_sent:
                self.logger.info("message sent... removing from queue")
            else:
                self.logger.info("the message couldn't be delivered to the queue... keeping it for next attempt")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def get_odds_from_fetcher(self, url):
        """
        Tells the fetcher to retrieve the odds for a given url
        """
        self.logger.info("passing url to fetcher and waiting for the odds")
        return self.odds_fetcher.fetch(url)


    def send_odds(self, odds):
        """
        Tells the producer to send a serialized version of the odds to the configured queue.
        """
        self.logger.info("passing the odds to the producer")
        return self.odds_producer.send_odds(odds)

class CalienteUrlProducer(Producer):
    def __init__(self, config):
        """
        Initialize producer instance.
        """
        super().__init__(config)
        self.logger = get_logger()
        self.logger.info(f"initializing {CalienteUrlProducer.__name__} with {config}")

    def send_url(self, url):
        """
        This method calls the inherited produce method to send a new url
        to the configured queue.
        """
        return self.produce(url)

class CalienteCacheCleaner(TimedWorker):
    WAIT_TIME = "wait_time"
    def __init__(self, config, cache_client):
        """
        Initialize cache cleaner instance
        """
        self.load_config(config)
        super().__init__(self.wait_time)
        self.logger = get_logger()
        self.cache_client = cache_client

    def load_config(self, config):
        self.wait_time = config[CalienteCacheCleaner.WAIT_TIME]

    def do_work(self):
        """
        Tells the cache client to flush all the keys in the server
        """
        self.logger.info("flushing all keys in cache server")
        self.cache_client.clean_cache()
