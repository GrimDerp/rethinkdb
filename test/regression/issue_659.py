#!/usr/bin/env python
# Copyright 2010-2014 RethinkDB, all rights reserved.

from __future__ import print_function

import sys, os, time

startTime = time.time()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, 'common')))
import driver, rdb_workload_common, utils

r = utils.import_python_driver()
dbName, tableName = utils.get_test_db_table()

numNodes = 2
numReplicas = 2

print("Starting cluster of %d servers (%.2fs)" % (numNodes, time.time() - startTime))
with driver.Cluster(initial_servers=numNodes, output_folder='.', wait_until_ready=True) as cluster:
    
    print("Establishing ReQL Connection (%.2fs)" % (time.time() - startTime))
    
    server = cluster[0]
    conn = r.connect(host=server.host, port=server.driver_port)
    
    print("Creating db/table %s/%s (%.2fs)" % (dbName, tableName, time.time() - startTime))
    
    if dbName not in r.db_list().run(conn):
        r.db_create(dbName).run(conn)
    
    if tableName in r.db_list().run(conn):
        r.table_drop(tableName).run(conn)
    r.db(dbName).table_create(tableName).run(conn)

    print("Increasing replication factor (%.2fs)" % (time.time() - startTime))
    r.db(dbName).table(tableName).reconfigure(shards=1, replicas=numReplicas).run(conn)
    r.db(dbName).table_wait().run(conn)
    cluster.check()

    print("Inserting some data (%.2fs)" % (time.time() - startTime))
    rdb_workload_common.insert_many(host=server.host, port=server.driver_port, database=dbName, table=tableName, count=20000)
    r.db(dbName).table_wait().run(conn)
    cluster.check()

    print("Decreasing replication factor (%.2fs)" % (time.time() - startTime))
    r.db(dbName).table(tableName).reconfigure(shards=1, replicas=1).run(conn)
    r.db(dbName).table_wait().run(conn)
    cluster.check()

    print("Increasing replication factor again (%.2fs)" % (time.time() - startTime))
    r.db(dbName).table(tableName).reconfigure(shards=1, replicas=numReplicas).run(conn)

    print("Confirming that the progress meter indicates a backfill happening (%.2fs)" % (time.time() - startTime))
    # ToDo: replace this with ReQL command once issue is done: https://github.com/rethinkdb/rethinkdb/issues/3115
    raise NotImplementedError('Wating for process table: https://github.com/rethinkdb/rethinkdb/issues/3115')
    
    cluster.check()
    
    print("Cleaning up (%.2fs)" % (time.time() - startTime))
    
    # The large backfill might take time, and for this test we don't care about it suceeding
    for server in cluster:
        server.close()

print("Done. (%.2fs)" % (time.time() - startTime))
