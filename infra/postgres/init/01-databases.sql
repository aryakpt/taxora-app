-- Runs once, when the Docker volume is first created.
CREATE DATABASE taxora_test OWNER taxora;
\connect taxora
CREATE EXTENSION IF NOT EXISTS vector;
\connect taxora_test
CREATE EXTENSION IF NOT EXISTS vector;
