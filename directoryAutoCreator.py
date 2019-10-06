import configparser, os, re, datetime, time, xlrd, xlsxwriter
from pathlib import Path
from os.path import exists
from shutil import copyfile

configFileName= 'config.ini'

config_file = os.path.join(Path(__file__).resolve().parent, configFileName)
config = configparser.ConfigParser()
config.read(config_file,encoding='UTF-8')


outputFolder= config['PATH']['OUTPUT_PATH'] 
indicator = config['SHEET']['FINDINGS_INDICATOR']


def makeDirectory(folderPath):
    if not exists(folderPath):
        os.makedirs(folderPath)


def getFindingsFiles(filesToFind):
    findingsFileName= config['FILE']['FINDINGS_FILE_NAME']
    sheetName = config['SHEET']['SHEET_NAME']
    rowIndicator= int(config['SHEET']['ROW_INDICATOR'])
    rowFileName= int(config['SHEET']['ROW_FILE_NAME'])
    sheetName = config['SHEET']['SHEET_NAME']
    
    findingsFileDict= {}
    
    xlsx = xlrd.open_workbook(findingsFileName)
    sheet = xlsx.sheet_by_name(sheetName)
    lineNo= 0
    
    for row in sheet._cell_values:
        if row[rowIndicator] == indicator and any(row[rowFileName].endswith(f'{extension}') for extension in filesToFind):
            lineNo += 1
            fileName= row[rowFileName]

            if fileName in findingsFileDict:
                findingsCounter= findingsFileDict[fileName]
                findingsCounter[1]= findingsCounter[1]+1
                findingsFileDict[fileName]= findingsCounter
            else:    
                findingsFileDict[fileName]= [lineNo, 1]
            
    return findingsFileDict


def extractFiles(path, findingsFileDict, fileSearchPattern):
    # r=root, d=directories, f = files
    for r, d, f in os.walk(path):
        for file in f:
            filePath= os.path.join(r, file)
            index= re.search(fileSearchPattern, filePath)
            if index:
                for fileName in findingsFileDict:
                    if fileName.lower().strip() in filePath.lower().strip():
                        itemList= findingsFileDict[fileName]
                        itemList.append(filePath)
                        itemList.append(file)
                        itemList.append(fileName)
                        findingsFileDict[fileName] = itemList


def getFolderSuffix(start, counter, noOfDigits= 3):
    if counter == 1:
        return '{0:0d}'.replace('d', str(noOfDigits)).format(start)
    else:
        return '{}_{}'.format('{0:0d}'.replace('d', str(noOfDigits)).format(start), '{0:0d}'.replace('d', str(noOfDigits)).format(start + counter-1))


def makeTestFile(outputPathTest, fileName, testClassTemplePath, packageName, className):
    testClass = open('{}\\Test{}'.format(outputPathTest, fileName), 'w', encoding= encoding)
    with open(testClassTemplePath, 'rt', encoding= encoding) as fp:
        for line in fp:
            if '<packageName>' in line:
                line= line.replace('<packageName>', packageName)
            elif '<ClassName>' in line:
                line= line.replace('<ClassName>', className)
            
            testClass.write(line)
    if not testClass.closed:
        testClass.close()



def process(findingsFileDict, encoding, folderPrefix, noOfDigits):
    currentPath= Path(__file__).resolve().parent
    outputRootPath= os.path.join(currentPath, outputFolder)
    packagePattern= config['OTHERS']['PACKAGE_PATTERN']
    testClassTemple= config['OTHERS']['TEST_CLASS_TEMPLATE']
    testClassTemplePath= os.path.join(currentPath, testClassTemple)
    regExPattern1= re.compile('\+\s*(\w+)\s*[\+;]*')

    for fileNameKey in findingsFileDict:
        findingsInfo= findingsFileDict[fileNameKey]
        start= findingsInfo[0]
        counter= findingsInfo[1]
        output= folderPrefix + getFolderSuffix(start, counter, noOfDigits)
        outputPath= os.path.join(outputRootPath, output)
        sourceFileName= findingsInfo[2]
        fileName= findingsInfo[3]
        findingsFileName= findingsInfo[4]
        fileExtensionIndex= re.search('\.', fileName)
        className= fileName[:fileExtensionIndex.start()]

        initOutputPath= findingsFileName.replace(fileName, '')
        outputPath= os.path.join(outputPath, initOutputPath)
        makeDirectory(outputPath)

        testFolder= initOutputPath.split('\\')[1]
        outputPathTest= outputPath.replace(testFolder, '{}\\{}'.format(testFolder, 'test'))
        makeDirectory(outputPathTest)
        
        with open(sourceFileName, 'rt', encoding= encoding) as fp:
            print("sourceFileName: %s" %sourceFileName)
            packageName= None
            lineNo= 0
            classFile = open(os.path.join(outputPath, fileName), 'w', encoding= encoding)
            
            for line in fp:
                lineNo += 1
                
                result= re.findall(packagePattern, line)
                if len(result) > 0:
                    packageName= 'test.{}'.format(result[0])
                
                
                result= regExPattern1.findall(line)
                if len(result)>0:
                    line = line.replace('\n', '  /* ??? */\n')

                classFile.write(line)
            
            if not classFile.closed:
                classFile.close()

            if not packageName:
                index= re.search('test', outputPathTest)
                packageName= outputPathTest[index.start():len(outputPathTest)-1].replace('\\','.')
            
            makeTestFile(outputPathTest, fileName, testClassTemplePath, packageName, className)


if __name__ == "__main__":
    try:
        start = datetime.datetime.now()
        
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
        print(f'Error found!\n{err}\n')
