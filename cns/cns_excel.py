#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Li Ding

# base packages
import os
import sys
import json
import logging
import codecs
import hashlib
import datetime
import time
import argparse
import urlparse
import re
import collections
import glob

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

from kgtool.core import *  # noqa
from kgtool.table import *  # noqa
from cns.cns_schema import *


# global constants
VERSION = 'v20180519'
CONTEXTS = [os.path.basename(__file__), VERSION]


"""
* load CnSchema instance
* dump in json for version checking
* generate information quality report
* draw schema diagram
* maintain property mapping

"""

MAP_NAME_URLPATTERN = {
    "schemaorgName": "http://schema.org/{}",
    "wikipediaName": "https://en.wikipedia.org/wiki/{}",
    "wikidataName": "https://www.wikidata.org/wiki/{}"
}

SCHEMA_EXCEL_HEADER = {
	"class": {
		"COPY": [
            "name",
            "nameZh",
            "version",
            "category",
			"descriptionZh",
			"descriptionZhSource",
			"description",
			"descriptionSource"
		],
		"SKIP": ["cnschemaName"]
	},
	"property": {
		"COPY": [
            "name",
			"nameZh",
            "version",
            "category",
			"descriptionZh",
			"descriptionZhSource",
			"description",
			"descriptionSource"
		],
		"SKIP": ["cnschemaName"]
	},
	"template": {
		"COPY": [
            "version",
            "minCardinality",
            "maxCardinality",
            "refClass",
            "refProperty",
            "propertyNameZh",
            "propertyAlternateName",
            "propertyRange",
            "propertySchema",
            "propertyDefinition",
            "propertyDefinitionSource",
            "propertyDefinitionZh",
            "propertyDefinitionZhSource"],
		"SKIP": []
	},
	"changelog": {
		"COPY": ["version", "datePublished", "name", "text"],
		"SKIP": []
	},
	"metadata": {
		"COPY": ["version", "proeprty", "value"],
		"SKIP": []
	}
}

SCHEMA_EXCEL_HEADER_SKIP = {
    "class": [  "cnschemaName",
             ],
    "property": [
                "cnschemaName",
                ],
    "template": [],
    "changelog": [],
}


def initCnsExcel():
    listSheetname = []
    mapDataTable = {}

    sheetname = "class"
    listSheetname.append(sheetname)
    mapDataTable[sheetname] = {
        "sheetname": sheetname,
        "rows":[],
        "columns": [ "version",
            "category",
            "name",
            "super",
            "supersededBy",
            "schemaorgName",
            "wikidataName",
            "wikipediaName",
            "cnschemaName",
            "nameZh",
            "alternateName",
            "descriptionZh",
            "descriptionZhSource",
            "description",
            "descriptionSource",
            ]
    }

    sheetname = "property"
    listSheetname.append(sheetname)
    mapDataTable[sheetname] = {
        "sheetname": sheetname,
        "rows":[],
        "columns": ["version",
            "category",
            "name",
            "super",
            "supersededBy",
            "schemaorgName",
            "wikidataName",
            "wikipediaName",
            "cnschemaName",
            "nameZh",
            "alternateName",
            "descriptionZh",
            "descriptionZhSource",
            "description",
            "descriptionSource",
            "domain",
            "range"
            ]
    }


    sheetname = "template"
    listSheetname.append(sheetname)
    mapDataTable[sheetname] = {
        "sheetname": sheetname,
        "rows":[],
        "columns":[
            "version",
            "category",
            "minCardinality",
            "maxCardinality",
            "refClass",
            "refProperty",
            "propertyNameZh",
            "propertyAlternateName",
            "propertyRange",
            "propertySchema",
            "propertyDefinition",
            "propertyDefinitionSource",
            "propertyDefinitionZh",
            "propertyDefinitionZhSource"
        ]
    }

    sheetname = "changelog"
    listSheetname.append(sheetname)
    mapDataTable[sheetname] = {
        "sheetname": sheetname,
        "rows":[],
        "columns":[
            "version",
            "name",
            "datePublished",
            "text"
        ]
    }

    sheetname = "metadata"
    listSheetname.append(sheetname)
    mapDataTable[sheetname] = {
        "sheetname": sheetname,
        "rows":[],
        "columns":[
            "version",
            "property",
            "value"
        ]
    }

    return listSheetname, mapDataTable


class CnsExcel():
    def __init__(self):
        #系统处理报告
        self.report = collections.defaultdict(list)

        #cnSchema存储
        self.schema = CnsSchema()


    def loadExcelSchema(self, filename):
        excelData = excel2json(filename)
        name = os.path.basename(filename).split(".")[0]
        self.schema.addMetadata("name", name)

        for sheet_name, items in excelData["data"].items():
            if self._loadSheetDefinition(sheet_name, items, "class"):
                pass
            elif self._loadSheetDefinition(sheet_name, items, "property"):
                pass
            elif self._loadSheetCardinality(sheet_name, items):
                pass
            elif self._loadSheetChangelog(sheet_name, items):
                pass
            elif self._loadSheetMetadata(sheet_name, items):
                pass
            else:
                msg = u"skip sheet {}".format( sheet_name)
                self.report["info"].append(msg)
                logging.info( msg )

        self.schema.build()

    def _isValidRow(self, item):
        # all valid definition has version number starting with "v"
        if not item[u"version"].startswith("v"):
            return False

        return True


    def _loadSheetMetadata(self,  sheet_name, items):
        xlabel = "metadata"

        if sheet_name == xlabel:
            pass
        else:
            return False

        cnsItemList = []
        for item in items:
            if not self._isValidRow(item):
                continue

            property = item["property"]
            value = item["value"]
            assert property
            assert value

            self.schema.addMetadata( property, value )

        return True

    def _loadSheetChangelog(self,  sheet_name, items):
        xlabel = "changelog"
        if sheet_name == xlabel:
            xtype = ["CnsChangelog", "CnsMetadata", "Thing"]
        else:
            return False


        cnsItemList = []
        for item in items:
            if not self._isValidRow(item):
                continue

            name = item["name"]
            assert name
            xid = "http://meta.cnschema.org/changelog/{}".format(name)

            cnsItem = {
                "@type": xtype,
                "@id": xid,
                "name": name,
            }
            for p,v in item.items():
                self._copy_values(cnsItem, p, v, sheet_name)

            self.schema.addMetadata( xlabel, cnsItem )

        return True

    def _cardinality2definition(self, cnsItem):
        if cnsItem["propertySchema"] == "":
            name = cnsItem["refProperty"]
            xid = "http://cnschema.org/{}".format(name)
            cnsItemDefinition = {
                "@id": xid,
                "@type": ["rdf:Property", "CnsDefinition","CnsMetadata", "Thing"],
                "name": name,
                "category": "property-template",
                "nameZh": cnsItem["propertyNameZh"],
                "alternateName": cnsItem["propertyAlternateName"],
                "rdfs:domain": cnsItem["refClass"],
                "rdfs:range": cnsItem["propertyRange"],
            }

            self.schema.addDefinition( cnsItemDefinition )

    def _loadSheetCardinality(self,  sheet_name, items):


        xlabel = "template"
        if sheet_name == xlabel:
            xtype = ["CnsTemplate", "CnsMetadata", "Thing"]
        else:
            return False

        for item in items:
            if not self._isValidRow(item):
                continue

            name = "{}_{}".format(
                item["refClass"],
                item["refProperty"]
            )

            xid = "http://meta.cnschema.org/template/{}".format( name )
            cnsItem = {
                "@type": xtype,
                "@id": xid,
                "name": name
            }
            for p,v in item.items():
                self._copy_values(cnsItem, p, v, sheet_name)

            self.schema.addMetadata( "template", cnsItem )

            self._cardinality2definition(cnsItem)

        return True

    def _copy_values(self, cnsItem, p, v, sheet_name):
        if p in SCHEMA_EXCEL_HEADER[sheet_name]["COPY"]:
            cnsItem[p] = v
        elif p in SCHEMA_EXCEL_HEADER[sheet_name]["SKIP"]:
            pass
        elif p == "":
            pass
        else:
            msg = u"warn: column {} not in COPY/SKIP in sheet {}".format( p, sheet_name)
            self.report["warn"].append(msg)
            #logging.warn( msg )
            #logging.warn( json4debug( cnsItem ) )

    def _loadSheetDefinition(self, sheet_name, items, xlabel ):
        if not sheet_name == xlabel:
            return False
        #logging.info( xlabel )

        if "class" == xlabel:
            xtype = ["rdfs:Class", "CnsDefinition", "CnsMetadata", "Thing"]
        elif "property" == xlabel:
            xtype = ["rdf:Property", "CnsDefinition","CnsMetadata", "Thing"]
        else:
            assert False

        for item in items:
            if not self._isValidRow(item):
                continue

            name = item["name"]
            assert name
            xid = "http://cnschema.org/{}".format(name)

            cnsItem = {
                "@type": xtype,
                "@id": xid,
                "name": name,
            }
            for p,v in item.items():
                self._convertDefinition(p, v, cnsItem, sheet_name)

            self.schema.addDefinition( cnsItem )

        return True

    def _convertDefinition(self, p, v, cnsItem, sheet_name):
        if not v:
            return

        if p  == "super":
            if sheet_name == "class":
                px = "rdfs:subClassOf"
            elif sheet_name == "property":
                px = "rdfs:subPropertyOf"
            else:
                assert False
            cnsItem[px] =  parseListValue(v)
        elif p  == "domain":
            px = "rdfs:domain"
            cnsItem[px] = v
        elif p  == "range":
            px = "rdfs:range"
            cnsItem[px] =  v
        elif p == "supersededBy":
            pass
        elif p in MAP_NAME_URLPATTERN:
            px = re.sub("Name", "Url", p)
            cnsItem[px] = MAP_NAME_URLPATTERN[p].format( v )
        elif p in ["alternateName"]:
            cnsItem[p] =  parseListValue(v)
        else:
            self._copy_values(cnsItem, p, v, sheet_name)




def task_excel2jsonld(args):
    logging.info( "called task_excel2jsonld" )
    cnsExcel = CnsExcel()
    filename = args["input_file"]
    cnsExcel.loadExcelSchema(filename)
    if len(cnsExcel.report["warn"])>0:
        logging.info(json4debug(cnsExcel.report["warn"]))
        assert False

    filename_output = args["output_file"]
    cnsExcel.schema.exportJsonLd(filename_output)

    jsondata = file2json(filename_output)
    report = cnsExcel.schema.initReport()
    cnsExcel.schema.cnsValidateRecursive(jsondata, report)
    if len(report["bugs"])>2:
        logging.info(json4debug(report))
        assert False


    xdebug_file = os.path.join(args["debug_dir"],os.path.basename(args["output_file"]))
    filename_debug = xdebug_file+u".debug"
    cnsExcel.schema.exportDebug(filename_debug)

    from pyld import jsonld
    doc = file2json(filename_output)
    normalized = jsonld.normalize(
        doc, {'algorithm': 'URDNA2015', 'format': 'application/n-quads'})
    filename_ntriples = args["output_file"].replace("jsonld","nq")
    lines2file([normalized], filename_ntriples )

    # RDF lib does not parse JSON-LD correctly
    #from rdflib import Graph, plugin
    #from rdflib.serializer import Serializer
    #testrdf = u"\n".join(file2iter(filename_output))
    #g = Graph().parse(data=testrdf, format='json-ld')
    #content = g.serialize(format='nt')
    #filename_ntriples = args["output_file"].replace("jsonld","nt")
    #lines2file([content], filename_ntriples )


if __name__ == "__main__":
    logging.basicConfig(format='[%(levelname)s][%(asctime)s][%(module)s][%(funcName)s][%(lineno)s] %(message)s', level=logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)

    optional_params = {
        '--input_file': 'input file',
        '--output_file': 'output file',
        '--debug_dir': 'debug directory',
    }
    main_subtask(__name__, optional_params=optional_params)

"""
    excel2jsonld  and n-quad

    mv ~/Downloads/cns_top.xlsx ~/haizhi/git/kgtool/local/
    python cns/cns_excel.py task_excel2jsonld --input_file=local/cns_top.xlsx --output_file=schema/cns_top.jsonld --debug_dir=local/

    python cns/cns_excel.py task_excel2jsonld --input_file=local/cns_schemaorg.xls --output_file=schema/cns_schemaorg.jsonld --debug_dir=local/

    mv ~/Downloads/cns_organization.xlsx ~/haizhi/git/kgtool/local/
    python cns/cns_excel.py task_excel2jsonld --input_file=local/cns_organization.xlsx --output_file=schema/cns_organization.jsonld --debug_dir=local/


"""
