## FlowETL sample deployment

This directory contains the files necessary to do an example deployment of FlowETL,
which will ingest sample calls data from an external PostgreSQL database and sample
SMS data from CSV files.

The remainder of this README describes the steps to set up this deployment and run
the ingestion process. For the initial steps of building the relevant docker images,
you need a local clone of the FlowKit repository. For simplicity, the steps below
assume that you are running them from within this local clone, inside the
directory `flowetl/deployment_example/`.

In a production deployment, you would simply upload the docker images directly to the
server (or pull them directly from Docker Cloud if the server has internet connection).
However, for development and testing it is useful to build the images locally, which is
the method described here.
Note that some other parts of the setup - e.g. using a docker swarm or setting up a
local registry - are not strictly needed for a local example deployment, but we describe
them here in order to mimic a production setup as closely as possible.


### Initialise docker swarm mode and set up a local docker registry

FlowETL and FlowDB are going to be deployed using a docker swarm.
To do this, first make the machine you're working on a docker swarm manager.
```
docker swarm init

# Note: if the previous command fails, use the following one with the public IP address of this machine
#docker swarm init --advertise-addr=<ip_address_of_vm>
```

We also start a local docker registry. This is where we will push the docker images
for FlowETL and FlowDB so that they can be deployed to the swarm.
```
docker service create --name registry --publish published=5000,target=5000 registry:2
```

You can use the following command to verify that the registry is working (this should simply print '{}').
```
curl -w '\n' http://127.0.0.1:5000/v2/
```


### Set up an external PostgreSQL database to ingest from

For testing purposes, we build a separate PostgreSQL database (`ingestion_db`)
which includes some sample data and which will serve as the "external" database
from which we ingest data into FlowDB.

First we set the relevant environment variables, which are defined in the file `defaults_ingestion_db.env`.
```bash
set -a && source ./defaults_ingestion_db.env && set +a
```

Then we can build and deploy the database.
```bash
make build-and-deploy-ingestion_db
```

Note that this step also creates an overlay network called `ingestion_db_overlay`.
```bash
$ docker network ls -f name=ingestion_db_overlay
NETWORK ID          NAME                   DRIVER              SCOPE
ky5npo99ik0z        ingestion_db_overlay   overlay             swarm
```
This network allows the `flowdb` docker container to talk to the `ingestion_db` container which we just created.


### Sample data in IngestionDB

The `ingestion_db` instance contains sample data in the table `events.cdr` (generated by the
scripts `ingestion_db/sql/01_create_events_cdr_table` and `ingestion_db/sql/02_insert_sample_data.sql`).

You can connect to the database by running the following convenience Makefile command.
(Of course, a regular `psql` connection command work as well.)
```bash
make connect-ingestion_db
```

Let's check that the sample data is present:
```
ingestion_db=# SELECT COUNT(*) FROM events.cdr;
 count
--------
 500000
(1 row)

ingestion_db=# SELECT * FROM events.cdr LIMIT 3;
          event_time           |                              msisdn                              | cell_id
-------------------------------+------------------------------------------------------------------+---------
 2019-08-16 11:02:21.606812+00 | cfcd208495d565ef66e7dff9f98764dacfcd208495d565ef66e7dff9f98764da |  16284
 2019-08-16 11:02:22.606812+00 | c4ca4238a0b923820dcc509a6f75849bc4ca4238a0b923820dcc509a6f75849b |  42276
 2019-08-16 11:02:23.606812+00 | c81e728d9d4c2f636f067f89cc14862cc81e728d9d4c2f636f067f89cc14862c |  94994
(3 rows)
``` 

### Set up a docker stack with FlowDB and FlowETL

Set relevant environment variables for FlowDB and FlowETL.
Most of them are pre-defined in `defaults.env`, but we need to set
the path to the local clone of the FlowKit repo manually (this variable
is needed to build the docker images for FlowDB and FlowETL).

```bash
set -a && source ./defaults_flowkit.env && set +a
export LOCAL_FLOWKIT_REPO=$(pwd)/../..
```

Build FlowDB and FlowETL.
```
make build-flowdb        # this may take ~3-4 minutes
make build-flowetl       # this is quick (~30s)
```

Next, push the docker images which we just built to the local registry.
```
make push-to-local-registry  # this may take a couple of minutes the first time around
```

Finally, deploy the docker stack.
```
make deploy-flowkit-stack
```

After a few seconds, everything should be up and running.
You can use `docker service ls` to verify this.
```bash
$ docker service ls
ID                  NAME                              MODE                REPLICAS            IMAGE                           PORTS
cyuqezddz3ck        flowetl_test_flowdb               replicated          1/1                 127.0.0.1:5000/flowdb:latest    *:12000->5432/tcp
g2qicejmgc5g        flowetl_test_flowetl              replicated          1/1                 127.0.0.1:5000/flowetl:latest   *:8080->8080/tcp
p9qkn3k6lsec        flowetl_test_flowetl_airflow_db   replicated          1/1                 postgres:11                     *:5433->5432/tcp
cr06cx2pqiaq        registry                          replicated          1/1                 registry:2                      *:5000->5000/tcp
```
Note that the `ingestion_db` container does _not_ show up in this list (but it will show up
if you run `docker ps`). This is because it has been deployed separately, not as part of
this stack - which is intentional since we want to treat it like an external database that
exists outside the FlowKit setup.

You can connect to the databases `flowdb` and `flowetl_airflow_db` (= the database which the
Airflow instance in `flowetl` uses internally) by running the following convenience
Makefile commands. (Of course, regular `psql` connection commands work as well.)
```bash
make connect-flowdb
make connect-flowetl_airflow_db
```

If you want to shut down the docker services in the stack, use the following command.
```bash
make shut-down-stack-without-purging-volumes
```
This calls the script `shut_down_docker_stack.sh`, which ensures that any networks set up by docker
will be removed as well (which otherwise can be a bit flaky; see references in the script for details).
In rare cases this still fails, but a restart of the docker daemon should fix it and remove any
spurious networks. Note that this command retains the docker volumes used by the databases so that
when you bring up the stack again the data is still available (including bookkeeping data about
previous Airflow runs).


_Note:_ there is a convenience Makefile target to run the build and deploy commands for FlowDB and FlowETL in a single step:
```bash
make build-and-deploy-flowkit-stack
```
This is useful if you make changes to the source code, in which case you need to re-build the docker images
for these changes to be picked up.


### Create foreign data wrappers to connect FlowDB to IngestionDB

Run the following from within `flowdb` (you can connect to flowdb by running `make connect-flowdb`).
```
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

CREATE SERVER IF NOT EXISTS ingestion_db_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'ingestion_db',
        port '5432',
        dbname 'ingestion_db'
    );

CREATE USER MAPPING IF NOT EXISTS FOR flowdb
    SERVER ingestion_db_server
    OPTIONS (
        user 'ingestion_db',
        password 'etletl'
    );

CREATE FOREIGN TABLE sample_data_fdw (
        event_time TIMESTAMPTZ,
        msisdn TEXT,
        cell_id TEXT
    )
    SERVER ingestion_db_server
    OPTIONS (schema_name 'events', table_name 'cdr');
```

This creates one foreign data wrapper within `flowdb`: `sample_data_fdw` wraps the actual data itself and acts as the "source" in the ETL pipeline.

Let's verify that this was set up correctly, so that `flowdb` can now read data remotely from `ingestion_db`:
```
flowdb=# SELECT * FROM sample_data_fdw LIMIT 3;
          event_time           |                              msisdn                              | cell_id
-------------------------------+------------------------------------------------------------------+---------
 2019-08-17 10:44:31.173343+00 | cfcd208495d565ef66e7dff9f98764dacfcd208495d565ef66e7dff9f98764da |  72424
 2019-08-17 10:44:32.173343+00 | c4ca4238a0b923820dcc509a6f75849bc4ca4238a0b923820dcc509a6f75849b |  59569
 2019-08-17 10:44:33.173343+00 | c81e728d9d4c2f636f067f89cc14862cc81e728d9d4c2f636f067f89cc14862c |  81878
(3 rows)
```


### Run Airflow

At this point you have the following:

- An instance of `ingestion_db` with some sample data in the table `events.cdr`
- An instance of `flowdb` with a foreign table called `sample_data_fdw` which wraps the `events.cdr` table in `ingestion_db`.


Let's start the ingestion DAGs via the Airflow web interface.

- Navigate to http://localhost:8080, which should present you with the Airflow web interface.
- Log in using the username and password specified by `FLOWETL_AIRFLOW_ADMIN_USERNAME` and `FLOWETL_AIRFLOW_ADMIN_PASSWORD`. (The default stackfile sets these to `admin` and `password`.)
- Activate the `calls` and `sms` DAGs (by clicking on the "Off" buttons next to them so that they show "On" instead).
- Airflow will now run both DAGs, attempting to fill in any unprocessed dates,
  and trigger runs of the `calls` and `sms` DAGs for any unprocessed date it finds.
  
  This may take a minute or so - in order to see the progress, either reload your browser
  page, or click the "Refresh" button on one of the DAGs in the Airflow UI. (This is the
  button with the two circular arrows next to the button with the red cross.)

  You can also click on `calls` or `sms` in the "DAG" column (or alternatively navigate
  to http://localhost:8080/admin/airflow/tree?dag_id=calls or http://localhost:8080/admin/airflow/tree?dag_id=sms)
  to see a grid of squares indicating the various ingestion stages for each day of data found.

If all goes well, after a little while all the DAGs will have been completed and the data
will have been ingested into the `events.calls` and `events.sms` table. If you click on the
`calls`/`sms` DAGs you should see a bunch of green squares for the successfully
completed tasks for each ingestion date.

The result in `flowdb` should look something like this:
```
$ make connect-flowdb
psql "postgresql://flowdb:flowflow@127.0.0.1:11000/flowdb"
psql (11.1, server 11.4 (Debian 11.4-1.pgdg90+1))
Type "help" for help.

flowdb=# SELECT date, COUNT(*) FROM (SELECT datetime::date as date FROM events.calls) _ GROUP BY date ORDER BY DATE;
    date    | count
------------+-------
 2019-12-21 | 16368
 2019-12-22 | 86400
 2019-12-23 | 86400
 2019-12-24 | 86400
 2019-12-25 | 86400
 2019-12-26 | 86400
 2019-12-27 | 51632
(7 rows)

flowdb=# SELECT date, COUNT(*) FROM (SELECT datetime::date as date FROM events.sms) _ GROUP BY date ORDER BY DATE;
    date    | count
------------+-------
 2019-01-01 |   100
 2019-01-02 |   120
 (1 row)
```

The ETL process also runs some informative "post-ETL" queries after the ingestion process has finished.
The results are stored in the table `etl.post_etl_queries`:
```
flowdb=# SELECT * FROM etl.post_etl_queries;
  id |  cdr_date  | cdr_type | type_of_query_or_check | outcome | optional_comment_or_description |           timestamp
----+------------+----------+------------------------+---------+---------------------------------+-------------------------------
  1 | 2019-12-21 | calls    | count_location_ids     | 15101   |                                 | 2020-01-21 20:18:47.148012+00
  2 | 2019-12-21 | calls    | count_msisdns          | 16368   |                                 | 2020-01-21 20:18:48.14307+00
  3 | 2019-12-21 | calls    | count_duplicates       | 0       |                                 | 2020-01-21 20:18:48.334891+00
  4 | 2019-12-21 | calls    | count_added_rows       | 16368   |                                 | 2020-01-21 20:18:49.47824+00
  5 | 2019-12-21 | calls    | count_duplicated       | 0       |                                 | 2020-01-21 20:18:49.491777+00
  6 | 2019-12-22 | calls    | count_duplicated       | 0       |                                 | 2020-01-21 20:18:54.505273+00
  7 | 2019-12-22 | calls    | count_location_ids     | 57928   |                                 | 2020-01-21 20:18:55.078766+00
  9 | 2019-12-22 | calls    | count_added_rows       | 86400   |                                 | 2020-01-21 20:18:55.596859+00
  8 | 2019-12-22 | calls    | count_duplicates       | 0       |                                 | 2020-01-21 20:18:55.372054+00
 10 | 2019-12-22 | calls    | count_msisdns          | 86400   |                                 | 2020-01-21 20:19:10.088318+00
 11 | 2019-12-24 | calls    | count_added_rows       | 86400   |                                 | 2020-01-21 20:19:22.511206+00
 12 | 2019-12-24 | calls    | count_duplicated       | 0       |                                 | 2020-01-21 20:19:23.818199+00
 13 | 2019-12-23 | calls    | count_added_rows       | 86400   |                                 | 2020-01-21 20:19:24.470541+00
```