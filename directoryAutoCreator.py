import configparser, os, re, datetime, time, xlrd, xlsxwriter
import logging
from pathlib import Path
from os.path import exists, join
from shutil import copyfile
from distutils.util import strtobool

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

configFileName= 'config.ini'

currentPath= Path(__file__).resolve().parent
config_file = join(currentPath, configFileName)
config = configparser.ConfigParser()
config.read(config_file, encoding='UTF-8')


outputFolder= config['PATH']['OUTPUT_PATH'] 
indicator= config['SHEET']['FINDINGS_INDICATOR']
todo= config['OTHERS']['TODO']
isOverwriteFiles= strtobool(config['FLAG']['OVERWRITE_FILES'])
isAppendTodo= strtobool(config['FLAG']['TODO_MARKER_FLAG'])
isAppendIssueNo= strtobool(config['FLAG']['ISSUE_MARKER_FLAG'])

TO_FIX_PATTERN= config['REG_EX']['TO_FIX_PATTERN']
AFTER_BROKEN_CONCAT_PATTERN= config['REG_EX']['AFTER_BROKEN_CONCAT_PATTERN']

PACKAGE_NAME= 'packageName'
CLASS_NAME= 'className'
TARGET_ASSET= 'targetAsset'
TARGET_LINE_NO= 'targetLineNo'
TARGET_FINDINGS= 'targetFindings'


def makeDirectory(folderPath):
    if not exists(folderPath):
        os.makedirs(folderPath)


def getFindingsFiles(filesToFind):
    findingsFileName= config['FILE']['FINDINGS_FILE_NAME']
    sheetName = config['SHEET']['SHEET_NAME']
    rowIndicator= int(config['SHEET']['ROW_INDICATOR'])
    rowFileName= int(config['SHEET']['ROW_FILE_NAME'])
    rowItemNo= int(config['SHEET']['ROW_ITEM_NO'])
    rowLineNo= int(config['SHEET']['ROW_LINE_NO'])
    rowFindings= int(config['SHEET']['ROW_LINE_CONTENT'])
    
    if not exists(findingsFileName):
        findingsFileName= join(currentPath, findingsFileName)

    findingsFileDict= {}
    
    xlsx = xlrd.open_workbook(findingsFileName)
    sheet = xlsx.sheet_by_name(sheetName)
    
    for row in sheet._cell_values:
        if row[rowIndicator] == indicator and any(row[rowFileName].endswith(f'{extension}') for extension in filesToFind):
            fileName= row[rowFileName]
            itemNo= int(row[rowItemNo])
            issueLineNo= None
            issueLineNoIndex= re.search(r'\((\w*)', row[rowLineNo])
            if issueLineNoIndex:
                issueLineNo= int(row[rowLineNo][issueLineNoIndex.start()+1:issueLineNoIndex.end()])

            if fileName in findingsFileDict:
                findingsCounter= findingsFileDict[fileName]
                findingsCounter[1]= findingsCounter[1]+1
                issuesDict= findingsCounter[2]
                lineNoDict= findingsCounter[3]
            else:
                issuesDict= {}
                lineNoDict= {}
                findingsFileDict[fileName]= [itemNo, 1, issuesDict, lineNoDict]

            issueDetails= []
            issueDetails.append(itemNo)
            issueDetails.append(fileName)
            issueDetails.append(row[rowLineNo])
            issueDetails.append(row[rowFindings])
            issuesDict[itemNo]= issueDetails
            if not issueLineNo:
                lineNoDict[issueLineNo]= itemNo
            
    return findingsFileDict


def extractFiles(path, findingsFileDict, fileSearchPattern):
    # r=root, d=directories, f = files
    for r, d, f in os.walk(path):
        for file in f:
            filePath= join(r, file)
            index= re.search(fileSearchPattern, filePath)
            if index:
                for fileName in findingsFileDict:
                    findingsFileName= fileName.lower().strip()
                    srcFilePath= filePath.lower().strip()
                    indexSrc= re.search('src', filePath)
                    if indexSrc:
                        srcFilePath= srcFilePath[indexSrc.end():]
                    
                    if findingsFileName in srcFilePath or srcFilePath in findingsFileName:
                        itemList= findingsFileDict[fileName]
                        itemList.append(filePath)
                        itemList.append(file)
                        itemList.append(fileName)
                        findingsFileDict[fileName] = itemList


def getFolderSuffix(start, counter, noOfDigits= 3):
    if counter == 1:
        return '{0:0d}'.replace('d', str(noOfDigits)).format(start)
    else:
        return '{}-{}'.format('{0:0d}'.replace('d', str(noOfDigits)).format(start), '{0:0d}'.replace('d', str(noOfDigits)).format(start + counter-1))


def makeTestFile(outputPathTest, testClassTemplePath, testFileDict):
    packageName= testFileDict[PACKAGE_NAME]
    className= testFileDict[CLASS_NAME]
    targetAsset=  testFileDict[TARGET_ASSET].replace('\\','\\\\')
    targetLineNo= testFileDict[TARGET_LINE_NO]
    targetFindings= testFileDict[TARGET_FINDINGS]

    testFileName= '{}\\Test{}.java'.format(outputPathTest, className)
    testClass = open(testFileName, 'w', encoding= encoding)
    with open(testClassTemplePath, 'rt', encoding= 'utf-8') as fp:
        for line in fp:
            if '<packageName>' in line:
                line= line.replace('<packageName>', packageName)
            elif '<ClassName>' in line:
                line= line.replace('<ClassName>', className)
            elif '<targetAsset>' in line:
                line= line.replace('<targetAsset>', targetAsset)
            elif '<targetLineNo>' in line:
                line= line.replace('<targetLineNo>', targetLineNo)
            elif '<targetFindings>' in line:
                line= line.replace('<targetFindings>', targetFindings.replace('"','\\"'))
            
            testClass.write(line)
    if not testClass.closed:
        testClass.close()
    
    return testFileName


def process(findingsFileDict, encoding, folderPrefix, noOfDigits):
    outputRootPath= join(currentPath, outputFolder)
    testFileOutputPath= config['PATH']['TEST_PATH']
    packagePattern= config['OTHERS']['PACKAGE_PATTERN']
    testClassTemple= config['OTHERS']['TEST_CLASS_TEMPLATE']
    testClassTemplePath= join(currentPath, testClassTemple)
    regExPattern1= re.compile(TO_FIX_PATTERN)
    regExPattern2= re.compile(AFTER_BROKEN_CONCAT_PATTERN)
    

    for fileNameKey in findingsFileDict:
        findingsInfo= findingsFileDict[fileNameKey]
        
        start= findingsInfo[0]
        counter= findingsInfo[1]
        issuesDict= findingsInfo[2]
        lineNoFindings= findingsInfo[3]
        sourceFileName= findingsInfo[4]
        fileName= findingsInfo[5]
        findingsFileName= findingsInfo[6]
        className= fileName[:re.search('\.', fileName).start()]

        itemOutputFolder= folderPrefix + getFolderSuffix(start, counter, noOfDigits)
        outputPath= join(outputRootPath, itemOutputFolder)
        
        initOutputPath= findingsFileName.replace(fileName, '')
        outputSourcePath= join(outputPath, initOutputPath)
        makeDirectory(outputSourcePath)

        initOutputPathSplitted= initOutputPath.split('\\')
        outputTestFolder= initOutputPath.replace(initOutputPathSplitted[1], '{}\\{}'.format(initOutputPathSplitted[1], 'test'))
        outputTestPath= join(outputPath, outputTestFolder)
        makeDirectory(outputTestPath)        

        with open(sourceFileName, 'rt', encoding= encoding) as fp:
            print("SourceFileName: %s" %sourceFileName)
            packageName= None
            lineNo= 0
            isBrokenConCat= False
            classFile = open(join(outputSourcePath, fileName), 'w', encoding= encoding)
            
            for line in fp:
                lineNo += 1

                result= re.findall(packagePattern, line)
                if len(result) > 0:
                    packageName= 'test.{}'.format(result[0])
                
                if isAppendTodo:
                    if isBrokenConCat and not line.strip().startswith(('//','/*')) :
                        result= regExPattern2.search(line) 
                        if result:
                            line = line.replace('\n',  '  {} [Broken Concat]\n'.format(todo))
                        isBrokenConCat= False

                    if line.strip().endswith('+'):
                        isBrokenConCat= True
                    
                    result= regExPattern1.findall(line)
                    if len(result)>0:
                        line = line.replace('\n',  '  {}\n'.format(todo))

                if isAppendIssueNo and lineNo in lineNoFindings:
                    line = line.replace('\n',  '  {}  [Issue No: {}]\n'.format(todo, lineNoFindings[lineNo]))

                classFile.write(line)
            
            if not classFile.closed:
                classFile.close()

            if not packageName:
                index= re.search('test', outputTestPath)
                packageName= outputTestPath[index.start():len(outputTestPath)-1].replace('\\','.')

            for i in range(counter):
                index= start + i
                newClassName= '{}{}'.format(className, str(index))
                testFileDict= {}
                testFileDict[PACKAGE_NAME]= packageName
                testFileDict[CLASS_NAME]= newClassName
                testFileDict[TARGET_ASSET]= findingsFileName
                testFileDict[TARGET_LINE_NO]= issuesDict[index][2]
                testFileDict[TARGET_FINDINGS]= issuesDict[index][3]

                testFileName= makeTestFile(outputTestPath, testClassTemplePath, testFileDict)
                
                originalTestOutputPath= join(testFileOutputPath, outputTestFolder.replace('{}\\'.format(initOutputPathSplitted[0]),''))
                makeDirectory(originalTestOutputPath)

                workspaceTestFileName= '{}\\Test{}'.format(originalTestOutputPath, fileName.replace(className, newClassName))

                if not isOverwriteFiles and exists(workspaceTestFileName):
                    pass
                else:
                    copyfile(testFileName, workspaceTestFileName)

if __name__ == "__main__":
    try:
        start = datetime.datetime.now()
        print(f'\nInitializing...\nTime started: {start}')
        
        sourcePath= config['PATH']['SOURCE_CODE_PATH']
        filesSearchPattern = config['OTHERS']['FILES_SEARCH_PATTERN']
        filesToFind = config['OTHERS']['FILES_TO_FIND']
        folderPrefix = config['PATH']['OUTPUT_FOLDER_PREFIX']
        noOfDigits = config['OTHERS']['NO_OF_DIGITS']
        
        findingsFileDict= getFindingsFiles(filesToFind)
        extractFiles(sourcePath, findingsFileDict, filesSearchPattern)

        encoding= config['OTHERS']['ENCODING']
        process(findingsFileDict, encoding, folderPrefix, noOfDigits)
        
        finish = datetime.datetime.now()
        print(f'\nTime elapsed:\n{finish - start}')
    except Exception as err:
        logger.error(str(err), exc_info=True)
        input("")
