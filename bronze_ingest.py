from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, input_file_name

base_dir = Path(__file__).resolve().parent
landing_dir = base_dir / "landing" / "transactions"
landing_files = [str(path) for path in landing_dir.glob("*.csv")]
bronze_path = str(base_dir / "bronze" / "transactions")

if not landing_files:
    raise FileNotFoundError(f"No CSV files found in landing folder: {landing_dir}")

print(f"Reading {len(landing_files)} file(s) from {landing_dir}")

Path(bronze_path).mkdir(parents=True, exist_ok=True)

spark = (
    SparkSession.builder
        .appName("bronze_ingest")
        .config("spark.jars.packages", "io.delta:delta-core_2.13:2.4.0")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
)

# Step 1: read raw CSV files from the landing zone
raw_df = (
    spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(landing_files)
)

# Step 2: add simple metadata for auditing
raw_df = raw_df.withColumn("ingest_time", current_timestamp()) \
               .withColumn("source_file", input_file_name())

# Step 3: write the raw data to the Bronze layer in Delta format
raw_df.write.format("delta") \
      .mode("append") \
      .save(bronze_path)

print(f"Wrote {raw_df.count()} rows into Bronze at {bronze_path}")

# Optional: read back a few rows to verify
bronze_df = spark.read.format("delta").load(bronze_path)
bronze_df.show(5, truncate=False)

spark.stop()
