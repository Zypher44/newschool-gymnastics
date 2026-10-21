import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const directory=process.argv[2];
const data=JSON.parse(await fs.readFile(`${directory}/schema.json`,'utf8'));
const book=Workbook.create();
for(const [name,headers] of Object.entries(data.schemas)) {
 const sheet=book.worksheets.add(name);
 sheet.showGridLines=false;
 sheet.getRangeByIndexes(0,0,1,headers.length).values=[headers];
 sheet.getRangeByIndexes(0,0,20,headers.length).format.font={name:'Arial',size:11};
 sheet.getRangeByIndexes(0,0,1,headers.length).format={fill:'#1E40AF',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:32,horizontalAlignment:'center',verticalAlignment:'center'};
 sheet.getRangeByIndexes(1,0,19,headers.length).format.numberFormat='@';
 for(let col=0;col<headers.length;col++)sheet.getRangeByIndexes(0,col,20,1).format.columnWidth=headers[col]==='email'?29:headers[col]==='groups'||headers[col]==='athlete_ids'?25:19;
 sheet.freezePanes.freezeRows(1);
 if(name==='Coaches')sheet.getRange('G2:G1501').dataValidation={rule:{type:'list',values:['coach','head_coach']}};
}
const instructions=book.worksheets.add('Instructions');
instructions.showGridLines=false;
instructions.getRangeByIndexes(0,0,data.instructions.length,2).values=data.instructions;
instructions.getRange('A1:B14').format.font={name:'Arial',size:11};
instructions.getRange('A1').format.font={name:'Arial',size:14,bold:true,color:'#172554'};
instructions.getRange('A1:A14').format.columnWidth=42;
instructions.getRange('B1:B14').format.columnWidth=105;
instructions.getRange('B2:B14').format.wrapText=true;
instructions.getRange('A2:B2').format={fill:'#1E40AF',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'}};
instructions.getRange('A3:B14').format.rowHeight=34;
instructions.getRange('A1:B14').format.verticalAlignment='center';
book.recalculate();
console.log((await book.inspect({kind:'table',range:'Athletes!A1:I2',tableMaxRows:2,tableMaxCols:9})).ndjson);
for(const [name,range] of [...Object.keys(data.schemas).map(name=>[name,`A1:${name==='Athletes'?'I':'H'}4`]),['Instructions','A1:B14']]) {
 const preview=await book.render({sheetName:name,range,scale:1,format:'png'});
 await fs.writeFile(`${directory}/${name.replace(/[^a-z]/gi,'_')}.png`,new Uint8Array(await preview.arrayBuffer()));
}
const output=await SpreadsheetFile.exportXlsx(book);await output.save(`${directory}/roster-template.xlsx`);
