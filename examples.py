"""Sets up few-shot examples for SQL generation using semantic similarity."""

import logging
# LangChain imports (keep existing ones)
from langchain_community.vectorstores import FAISS
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_core.prompts import FewShotChatMessagePromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# Add imports for other potential providers if needed
# from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

import config

# Attempt to import pymongo, but don't fail if it's not needed/installed
try:
    import pymongo
except ImportError:
    pymongo = None

logger = logging.getLogger(__name__)

# --- Hardcoded Local Examples (Fallback) ---
_local_examples = [
    {
        "id": "local-1", "natural_language_query": "Hoe vaak heeft Feyenoord gewonnen van Ajax?",
        "query": "SELECT COUNT(*) FROM matches WHERE (((homeClubName = 'Feyenoord' OR homeClubId = (SELECT clubId FROM clubs WHERE clubName='Feyenoord')) AND (awayClubName = 'Ajax' OR awayClubId = (SELECT clubId from clubs WHERE clubName='Ajax')) AND homeClubFinalScore > awayClubFinalScore) OR ((homeClubName = 'Ajax' OR homeClubId = (SELECT clubId FROM clubs WHERE clubName='Ajax')) AND (awayClubName = 'Feyenoord' OR awayClubId = (SELECT clubId FROM clubs WHERE clubName='Feyenoord')) AND awayClubFinalScore > homeClubFinalScore));"
    },
    {
        "id": "local-2", "natural_language_query": "Hoe vaak heeft hebben Coen Moulijn en Sjaak Swart tegelijk in een wedstrijd gescoord?",
        "query": "SELECT p1.playerName AS player1, p2.playerName AS player2, COUNT(DISTINCT g1.matchId) AS matches_together FROM goals g1 JOIN goals g2 ON g1.matchId = g2.matchId AND g1.playerId != g2.playerId JOIN players p1 ON g1.playerId = p1.playerId JOIN players p2 ON g2.playerId = p2.playerId WHERE (p1.playerName = 'Coen Moulijn' AND p2.playerName = 'Sjaak Swart')   OR (p1.playerName = 'Sjaak Swart' AND p2.playerName = 'Coen Moulijn') GROUP BY player1, player2;"
    },
    {
        "id": "local-3", "natural_language_query": "Wat is de grootste overwinning van Feyenoord op PSV?",
        "query": "SELECT m.dateAndTime, m.homeClubName, m.awayClubName, m.homeClubFinalScore, m.awayClubFinalScore FROM matches m WHERE (((homeClubName = 'Feyenoord' OR homeClubId = (SELECT clubId FROM clubs WHERE clubName='Feyenoord')) AND (awayClubName = 'PSV' OR awayClubId = (SELECT clubId from clubs WHERE clubName='PSV')) AND homeClubFinalScore > awayClubFinalScore) OR ((homeClubName = 'PSV' OR homeClubId = (SELECT clubId FROM clubs WHERE clubName='PSV')) AND (awayClubName = 'Feyenoord' OR awayClubId = (SELECT clubId FROM clubs WHERE clubName='Feyenoord')) AND awayClubFinalScore > homeClubFinalScore)) ORDER BY ABS(m.homeClubFinalScore - m.awayClubFinalScore) DESC, MAX(m.homeClubFinalScore, m.awayClubFinalScore) ASC, m.dateAndTime ASC LIMIT 5;"
    }
]


# --- Internal State Variables for Lazy Initialization ---
_examples = None
_llm = None
_embeddings = None
_few_shot_sql_examples = None

# --- Example Loading Logic ---

def _load_examples_from_mongodb():
    """Loads examples from MongoDB based on config."""
    if not pymongo:
        logger.error("MongoDB source selected, but 'pymongo' library is not installed. Cannot load examples from DB.")
        return None # Indicate failure

    if not config.EXAMPLE_DB_CONNECTION_STRING:
        logger.error("MongoDB source selected, but EXAMPLE_DB_CONNECTION_STRING is not set in .env. Cannot connect.")
        return None # Indicate failure

    client = None # Initialize client to None
    try:
        logger.info(f"Attempting to connect to MongoDB: {config.EXAMPLE_DB_NAME}/{config.EXAMPLE_DB_COLLECTION}")
        # Set a reasonable timeout
        client = pymongo.MongoClient(
            config.EXAMPLE_DB_CONNECTION_STRING,
            serverSelectionTimeoutMS=5000 # 5 seconds timeout
        )
        # The ismaster command is cheap and does not require auth. Forces connection check.
        client.admin.command('ismaster')
        logger.info("MongoDB connection successful.")

        db = client[config.EXAMPLE_DB_NAME]
        collection = db[config.EXAMPLE_DB_COLLECTION]

        # Fetch examples, ensuring required fields are present
        # Adjust projection if your documents have different field names
        fetched_examples = list(collection.find(
            {},
            {"_id": 0, "natural_language_query": 1, "query": 1}
        ))

        # Basic validation
        valid_examples = [
            ex for ex in fetched_examples
            if "natural_language_query" in ex and "query" in ex
        ]

        if not valid_examples:
             logger.warning(f"MongoDB query returned no valid examples from {config.EXAMPLE_DB_NAME}/{config.EXAMPLE_DB_COLLECTION}.")
             return [] # Return empty list, not None, as the query succeeded but found nothing

        logger.info(f"Successfully loaded {len(valid_examples)} examples from MongoDB.")
        # Add an 'id' if it's missing, useful for some LangChain components, though not strictly required by selector
        for i, ex in enumerate(valid_examples):
            ex.setdefault("id", f"db-{i+1}")
        return valid_examples

    except pymongo.errors.ConfigurationError as e:
        logger.error(f"MongoDB configuration error (check connection string?): {e}")
        return None # Indicate failure
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB connection timed out: {e}")
        return None # Indicate failure
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching examples from MongoDB: {e}")
        return None # Indicate failure
    finally:
        if client:
            client.close()
            logger.debug("MongoDB connection closed.")


def load_examples():
    """Loads examples based on the configured source (config.EXAMPLE_SOURCE)."""
    global _examples
    if _examples is None: # Only load once
        source = config.EXAMPLE_SOURCE
        logger.info(f"Attempting to load examples from source: '{source}'")

        if source == 'mongodb':
            db_examples = _load_examples_from_mongodb()
            if db_examples is not None:
                logger.info(f"Using {len(db_examples)} examples loaded from MongoDB.")
                _examples = db_examples
            else:
                logger.warning("Failed to load examples from MongoDB. Falling back to local examples.")
                _examples = _local_examples # Fallback to local
        elif source == 'local':
            logger.info(f"Using {len(_local_examples)} local hardcoded examples.")
            _examples = _local_examples
        else:
            logger.warning(f"Unknown EXAMPLE_SOURCE '{source}' configured. Defaulting to local examples.")
            _examples = _local_examples
    return _examples


# --- Lazy Initializer Functions ---

def get_llm():
    """Lazily initializes and returns the LangChain LLM."""
    global _llm
    if _llm is None:
        logger.info("Initializing LLM (first access)...")
        if not config.LLM_API_KEY and not getattr(config, "GOOGLE_API_KEY", None):
            logger.warning("LLM_API_KEY or GOOGLE_API_KEY not set. Cannot initialize LLM.")
            # Return None, subsequent checks will handle this
        else:
            try:
                if config.LLM_PROVIDER == "openai":
                    logger.info(f"Initializing OpenAI LLM (Model: {config.LLM_MODEL}).")
                    _llm = ChatOpenAI(api_key=config.LLM_API_KEY, model=config.LLM_MODEL)
                elif config.LLM_PROVIDER == "google":
                    logger.info(f"Initializing Google Gemini LLM (Model: {config.LLM_MODEL}).")
                    _llm = ChatGoogleGenerativeAI(
                        google_api_key=getattr(config, "GOOGLE_API_KEY", config.LLM_API_KEY),
                        model=config.LLM_MODEL,
                        temperature=0.2
                    )
                # Add elif blocks for other providers if needed
                else:
                    logger.error(f"Unsupported LLM_PROVIDER: {config.LLM_PROVIDER}")

                if _llm:
                    logger.info(f"LLM initialized successfully for provider: {config.LLM_PROVIDER}")

            except Exception as e:
                logger.error(f"Failed to initialize LLM for provider {config.LLM_PROVIDER}: {e}")
                _llm = None # Ensure it remains None on failure
    return _llm

def get_embeddings():
    """Lazily initializes and returns the LangChain Embeddings."""
    global _embeddings
    if _embeddings is None:
        logger.info("Initializing Embeddings (first access)...")
        if not config.LLM_API_KEY:
            logger.warning("LLM_API_KEY not set. Cannot initialize Embeddings.")
        else:
            try:
                if config.LLM_PROVIDER == "openai":
                    logger.info("Initializing OpenAI Embeddings.")
                    _embeddings = OpenAIEmbeddings(api_key=config.LLM_API_KEY)
                elif config.LLM_PROVIDER == "google-genai":
                    logger.info("Initializing Google Gemini Embeddings.")
                    _embeddings = GoogleGenerativeAIEmbeddings(
                        google_api_key=config.LLM_API_KEY
                    )
                # Add elif blocks for other providers if needed
                else:
                    # If LLM provider is unsupported, embeddings likely are too
                    logger.error(f"Unsupported LLM_PROVIDER for embeddings: {config.LLM_PROVIDER}")

                if _embeddings:
                    logger.info("Embeddings initialized successfully.")

            except Exception as e:
                logger.error(f"Failed to initialize Embeddings for provider {config.LLM_PROVIDER}: {e}")
                _embeddings = None # Ensure it remains None on failure
    return _embeddings


def get_few_shot_selector():
    """Lazily initializes and returns the FewShotChatMessagePromptTemplate."""
    global _few_shot_sql_examples
    if _few_shot_sql_examples is None:
        logger.info("Initializing Few-Shot Example Selector (first access)...")
        # Ensure examples and embeddings are loaded/initialized first
        current_examples = load_examples() # Load examples if not already loaded
        current_embeddings = get_embeddings() # Initialize embeddings if not already initialized

        if current_embeddings and current_examples: # Check examples list is not empty
            try:
                logger.info(f"Creating FAISS vector store from {len(current_examples)} examples.")
                vector_store = FAISS.from_texts(
                    [ex["natural_language_query"] for ex in current_examples],
                    current_embeddings,
                    metadatas=current_examples
                )
                example_selector = SemanticSimilarityExampleSelector(
                    vectorstore=vector_store,
                    k=min(3, len(current_examples)),
                    input_keys=["natural_language_query"],
                )
                example_prompt = ChatPromptTemplate.from_messages(
                    [
                        ("human", "{natural_language_query}"),
                        ("ai", "{query}"),
                    ]
                )
                _few_shot_sql_examples = FewShotChatMessagePromptTemplate(
                    example_selector=example_selector,
                    example_prompt=example_prompt,
                    input_variables=["natural_language_query"],
                )
                logger.info(f"Few-shot example selector initialized successfully with k={example_selector.k}.")
            except Exception as e:
                logger.error(f"Failed to create FAISS vector store or example selector: {e}. Few-shot examples will not be used.")
                _few_shot_sql_examples = None # Explicitly set to None on failure
        elif not current_examples:
            logger.warning("No examples loaded. Few-shot examples will not be used.")
            _few_shot_sql_examples = None
        else: # Embeddings not available
            logger.warning("Embeddings not available. Few-shot examples will not be used.")
            _few_shot_sql_examples = None

    return _few_shot_sql_examples
