# คำอธิบาย Workflow Diagram
## StaySense Phitsanulok: Accommodation Management and Semantic Search System

ไฟล์ที่เกี่ยวข้อง:
- โค้ดแผนภาพ (แก้ไขต่อได้): `staysense-workflow.mmd`
- ภาพประกอบการนำเสนอ: `staysense-workflow.svg`, `staysense-workflow.png`

---

## 1. ภาพรวมของระบบ

StaySense Phitsanulok เป็นระบบสารสนเทศเพื่อการบริหารจัดการและค้นหาที่พักในจังหวัดพิษณุโลก โดยใช้เทคนิคการค้นหาเชิงความหมาย (Semantic Search) ระบบรองรับผู้ใช้งาน 3 กลุ่ม คือ ผู้เยี่ยมชม (Guest) สมาชิก (Registered User) และผู้ดูแลระบบ (Administrator) โดยไม่มีฟังก์ชันเจ้าของที่พักและไม่มีระบบการจอง/ชำระเงิน แผนภาพจึงเน้นการค้นหา การแสดงรายละเอียด และการบริหารจัดการข้อมูลที่พักเท่านั้น

แผนภาพจัดเรียงจากบนลงล่าง (Top-to-Bottom) แบ่งออกเป็นกลุ่มการทำงาน (Subgraph) 8 กลุ่ม ได้แก่

1. จุดเริ่มต้นและการเลือกประเภทผู้ใช้งาน
2. Semantic Search Workflow (กระบวนการค้นหาเชิงความหมาย)
3. การเรียกดูรายละเอียดที่พัก
4. Member Registration Workflow (การสมัครสมาชิก)
5. Login and Authentication (การเข้าสู่ระบบ)
6. Registered User Functions (ฟังก์ชันของสมาชิก)
7. Administrator Functions + Manage Accommodation Data (CRUD) + Data Quality Verification Workflow
8. System Architecture and Component Integration (สถาปัตยกรรมทางเทคนิค)

---

## 2. คำอธิบายลำดับการทำงานของแต่ละกลุ่ม

### 2.1 จุดเริ่มต้นและการเลือกประเภทผู้ใช้งาน
`Start → Access StaySense Phitsanulok Website → Select User Type`

ผู้ใช้งานเข้าสู่เว็บไซต์ StaySense Phitsanulok ระบบให้เลือกประเภทผู้ใช้งาน 3 ทาง:
- **Guest** → เข้าสู่โหมดผู้เยี่ยมชม (ค้นหาและดูข้อมูลได้โดยไม่ต้องเข้าสู่ระบบ)
- **Registered User** → ไปยังหน้าจอเข้าสู่ระบบ (Enter Username and Password)
- **Administrator** → ไปยังหน้าจอเข้าสู่ระบบเดียวกัน แล้วระบบจะตรวจสอบสิทธิ์อีกชั้นหนึ่งภายหลัง

### 2.2 Semantic Search Workflow (กระบวนการค้นหาเชิงความหมาย)
กลุ่มนี้ใช้ร่วมกันทั้งผู้เยี่ยมชมและสมาชิก (Guest Mode และ Open Member Functions ต่างก็เชื่อมเข้าสู่ `Enter Natural-Language Query`)

ลำดับการทำงาน:
1. **Enter Natural-Language Query** – ผู้ใช้งานพิมพ์คำค้นหาด้วยภาษาธรรมชาติ เช่น "รีสอร์ตเงียบสงบใกล้ธรรมชาติ ราคาไม่เกิน 2,000 บาท"
2. **Select Search Filters** – เลือกเงื่อนไขเพิ่มเติม (ประเภทที่พัก อำเภอ ราคา จำนวนผู้เข้าพัก สิ่งอำนวยความสะดวก บรรยากาศ)
3. **Use Current Location (Optional)** – เลือกใช้ตำแหน่งปัจจุบันเพื่อค้นหาที่พักใกล้ฉัน
4. **Submit Search** → **Validate Search Input** (จุดตัดสินใจ)
   - **No** → Display Search Input Error Message → ย้อนกลับไปแก้ไขคำค้นหา
   - **Yes** → ส่งเข้าสู่กระบวนการค้นหาจริง
5. **Send Query to Back-end API** → **Query Preprocessing** (ทำความสะอาดข้อความ) → **Convert Query to Vector (Embedding)** (แปลงคำค้นหาเป็นเวกเตอร์)
6. **Retrieve Accommodation Vectors** (ฐานข้อมูลเวกเตอร์ที่จัดเก็บไว้) → **Calculate Semantic Similarity** (คำนวณความคล้ายคลึง) → **Apply Search Filters** (กรองตามเงื่อนไข) → **Rank Search Results** (จัดลำดับความเกี่ยวข้อง) → **Return Search Results**
7. **Matching Accommodation Found?** (จุดตัดสินใจ)
   - **No** → Display "No Matching Accommodation Found" → ย้อนกลับไปแก้ไขคำค้นหา
   - **Yes** → **Display Search Results**

### 2.3 การเรียกดูรายละเอียดที่พัก
`Display Search Results → Select Accommodation → View Accommodation Details`

จากหน้าแสดงผลลัพธ์ ผู้ใช้งานเลือกที่พักเพื่อดูรายละเอียด (ชื่อ ที่อยู่ พิกัด ราคา ประเภทห้อง สิ่งอำนวยความสะดวก รูปภาพ บรรยากาศ ช่องทางติดต่อ แหล่งที่มาของข้อมูล สถานที่สำคัญและระยะทาง) จากนั้นสามารถ **View Location on Map** และ **Share Accommodation Information** ได้ทั้งผู้เยี่ยมชมและสมาชิก หากผู้เยี่ยมชมต้องการบันทึกรายการโปรด (**Add to Favorites**) ระบบจะตรวจสอบสถานะการเข้าสู่ระบบก่อน (อธิบายในหัวข้อ 2.6) เมื่อผู้ใช้งานดูข้อมูลเสร็จสิ้นจะไปยัง **Finish Viewing Information → End**

### 2.4 Member Registration Workflow (การสมัครสมาชิก)
`Guest Mode → Register → Enter Account Information → Validate Account Information → Account Already Exists?`
- **Yes** → Display Duplicate Account Message → ย้อนกลับไปแก้ไขข้อมูลบัญชี
- **No** → Create User Account → Store Account in Database → Registration Successful → เข้าสู่หน้า Login

### 2.5 Login and Authentication (การเข้าสู่ระบบ)
ใช้ร่วมกันทั้งสมาชิกและผู้ดูแลระบบ:
`Enter Username and Password → Authenticate User → Authentication Successful?`
- **No** → Display Login Error → ย้อนกลับไปกรอกใหม่
- **Yes** → **Check User Role** แล้วแยกเส้นทาง:
  - **Registered User** → Open Member Functions
  - **Administrator** → Check Administrator Permission (จุดตัดสินใจอีกชั้น)
    - **Denied** → Display Access Denied Message → End
    - **Granted** → Open Administrator Dashboard

### 2.6 Registered User Functions (ฟังก์ชันของสมาชิก)
จากหน้า **Open Member Functions** สมาชิกเลือกใช้งานฟังก์ชันต่าง ๆ ได้แก่
- **Add to Favorites** → Check Login Status (Not Logged In → Redirect to Login / Logged In → Check Existing Favorite → Save Favorite to Database → Display Success Message)
- **View and Remove Favorites**, **View Search History**, **View Recently Viewed Accommodations**
- **Select Accommodations to Compare → Add to Comparison List → Compare Accommodation Information → Display Comparison Results**
- **Retrieve Search History and Favorites → Analyze Relevant Accommodation Information → Generate Recommendations → Display Recommended Accommodations**
- **Manage Personal Information** (จัดการข้อมูลส่วนตัว)
- **Logout → End**

### 2.7 Administrator Functions และการบริหารจัดการข้อมูล
`Open Administrator Dashboard → Select Management Function` แยกออกเป็นฟังก์ชันย่อย:
- Manage Accommodation Data (รายละเอียดในหัวข้อ CRUD ด้านล่าง)
- Manage Accommodation Types, Manage Room Types, Manage Amenities, Manage Accommodation Images, Manage Coordinates and Landmarks, Manage Data Source Information, Manage Users and Permissions
- Review Accommodation Information (เชื่อมสู่ Data Quality Verification Workflow)
- Update Semantic Search Index

ทุกฟังก์ชันย่อยสิ้นสุดที่ **Finish Data Management → Logout → End**

**Manage Accommodation Data Workflow (CRUD)**
`Select Operation` แยกเป็น 4 ทาง:
- **Add** → Enter Accommodation Information → Add Room Types → Add Amenities → Upload Images → Add Location and Coordinates → Add Important Places and Distances → Record Data Source and Verification Date → Information Valid?
  - **No** → Display Validation Message → ย้อนกลับไปแก้ไขข้อมูล
  - **Yes** → Save Accommodation to MySQL Database → Prepare Accommodation Text → Convert Accommodation Data to Vector → Save or Update Accommodation Vector → Publish Accommodation Information → Display Success Message
- **View** → View Accommodation Records
- **Edit** → Retrieve Existing Information → Modify Accommodation Information → Validate Updated Information → Update MySQL Database → Searchable Information Changed?
  - **Yes** → Update Semantic Search Data → Convert Updated Information to Vector → Replace Existing Accommodation Vector → Finish Update Process
  - **No** → Finish Update Process (ข้ามขั้นตอนแปลงเวกเตอร์ใหม่)
- **Delete / Unpublish** → Confirm Action?
  - **No** → ย้อนกลับไปหน้า Manage Accommodation Data
  - **Yes** → Change Accommodation Status or Delete Record → Update Database → Remove or Disable Semantic Search Vector → Display Success Message

> ข้อแนะนำ: ควรใช้การเปลี่ยนสถานะเป็น "Unpublished/Inactive" แทนการลบถาวร เพื่อป้องกันข้อมูลสูญหายและรองรับการตรวจสอบย้อนหลัง

**Data Quality Verification Workflow**
`Review Accommodation Information → Check Data Source (Google Maps, Official Website, Facebook Page, Booking Sites) → Compare Information from Multiple Sources → Check Accuracy → Check Completeness → Check Consistency → Check Duplicate Information → Check Current Information → Record Source URL → Record Verification Date → Save Verified Information`

### 2.8 System Architecture and Component Integration
กล่องนี้สรุปสถาปัตยกรรมทางเทคนิคของระบบแยกไว้ต่างหาก เพื่อไม่ให้เส้นเชื่อมยาวพาดผ่านแผนภาพหลักจนอ่านยาก โดยมีความหมายสอดคล้องกับกระบวนการในแผนภาพหลักดังนี้:

| องค์ประกอบในแผนภาพ | สอดคล้องกับขั้นตอนใดในแผนภาพหลัก |
|---|---|
| User Interface: Vue.js and Vite | ทุกจุดที่เป็น Input/Output (เช่น Enter Natural-Language Query, Display Search Results) |
| Send Request through API | Send Query to Back-end API, Submit Search, Save Accommodation to MySQL Database ฯลฯ |
| Back-end Server: Node.js and Express.js | รับคำร้องขอ ตรวจสอบข้อมูล (Validate...) และประสานงานกับฐานข้อมูล/บริการ Python |
| MySQL Database | โหนดรูปทรงกระบอกทั้งหมดในแผนภาพหลัก เช่น Store Account in Database, Save Accommodation to MySQL Database, Save Favorite to Database |
| Python Semantic Search Service | โหนด Subprocess (กรอบสองเส้น) ที่เกี่ยวกับ Query Preprocessing, Convert Query/Accommodation Data to Vector, Calculate Semantic Similarity |
| Return Processed Results / Display Results on User Interface | Return Search Results → Display Search Results ในแผนภาพหลัก |

---

## 3. สัญลักษณ์ที่ใช้ในแผนภาพ (Flowchart Notation)

| สัญลักษณ์ | รูปทรง | ความหมาย |
|---|---|---|
| Terminator | วงรี/แคปซูล ⬭ | จุดเริ่มต้น (Start) และจุดสิ้นสุด (End) ของกระบวนการ |
| Process | สี่เหลี่ยมผืนผ้า ▭ | ขั้นตอนการประมวลผลทั่วไป เช่น Create User Account, Update MySQL Database |
| Input/Output | สี่เหลี่ยมด้านขนาน ▱ | การรับข้อมูลจากผู้ใช้งานหรือการแสดงผลลัพธ์ เช่น Enter Natural-Language Query, Display Search Results |
| Decision | สี่เหลี่ยมข้าวหลามตัด ◇ | จุดตัดสินใจที่มีเงื่อนไข Yes/No กำกับทุกเส้นทางออก เช่น Validate Search Input, Account Already Exists? |
| Database | รูปทรงกระบอก 🛢 | ฐานข้อมูล MySQL หรือข้อมูลเวกเตอร์ (Vector Data) ที่จัดเก็บถาวร |
| Subprocess | สี่เหลี่ยมผืนผ้าเส้นคู่ ▤ | กระบวนการย่อยของ Semantic Search เช่น Query Preprocessing, Calculate Semantic Similarity |

---

## 4. ความหมายของเส้นเชื่อม (Connectors)

- **เส้นทึบ (Solid Arrow)** หมายถึง ลำดับการทำงานปกติ (Sequence Flow) ที่ไหลจากขั้นตอนหนึ่งไปยังอีกขั้นตอนหนึ่งภายในระบบเดียวกัน
- **เส้นประ (Dashed Arrow)** ใช้เฉพาะในกล่อง System Architecture เพื่อแสดงการเรียกใช้บริการระหว่างองค์ประกอบทางเทคนิค (เช่น Back-end เรียกใช้ MySQL Database หรือ Python Semantic Search Service) ซึ่งเป็นการเชื่อมโยงเชิงบริการ ไม่ใช่ลำดับเหตุการณ์ตรง ๆ
- **ป้ายกำกับ Yes/No บนเส้นที่ออกจาก Decision** ระบุเงื่อนไขของแต่ละเส้นทางอย่างชัดเจนทุกจุด (เช่น Information Valid? → Yes/No, Confirm Action? → Yes/No)
- **ป้ายกำกับอื่น ๆ** บนเส้นที่ไม่ใช่ Decision (เช่น Guest / Registered User / Administrator ที่ออกจาก Select User Type หรือ Add / View / Edit / Delete ที่ออกจาก Select Operation) ใช้ระบุทางเลือกของผู้ใช้งาน ไม่ใช่เงื่อนไข Yes/No เนื่องจากเป็นจุดแยกเมนู (Multi-way Branch) ไม่ใช่จุดตรวจสอบเงื่อนไข

---

## 5. ความหมายของสีที่ใช้แบ่งกลุ่มการทำงาน

| สี | กลุ่มการทำงาน |
|---|---|
| 🟦 ฟ้าอ่อน | ผู้เยี่ยมชม (Guest) และขั้นตอนที่ผู้เยี่ยมชมเข้าถึงได้ เช่น การค้นหา การดูรายละเอียดที่พัก |
| 🟩 เขียวอ่อน | สมาชิก (Registered User) และฟังก์ชันเฉพาะสมาชิก เช่น รายการโปรด การเปรียบเทียบ คำแนะนำ |
| 🟧 ส้มอ่อน | ผู้ดูแลระบบ (Administrator) และฟังก์ชันบริหารจัดการข้อมูล |
| 🟨 เหลือง | ขั้นตอนการยืนยันตัวตนและตรวจสอบความถูกต้องของข้อมูล (Authentication และ Validation) |
| 🟪 ม่วงอ่อน | กระบวนการค้นหาเชิงความหมาย (Semantic Search) ที่ประมวลผลด้วยภาษา Python |
| ⬛ เทา/น้ำเงินเข้ม | ฐานข้อมูล MySQL และข้อมูลเวกเตอร์ (Database) |
| 🟥 แดงอ่อน | ข้อความแจ้งเตือนข้อผิดพลาดหรือข้อมูลไม่ถูกต้อง (Error / Invalid Data) |
| 🟢 เขียว | จุดเริ่มต้นและจุดสิ้นสุดของกระบวนการ (Start / End) |

---

## 6. หมายเหตุสำหรับการนำไปใช้งาน

- ไฟล์ `staysense-workflow.mmd` เปิดแก้ไขได้ทันทีด้วยโปรแกรมที่รองรับ Mermaid เช่น VS Code (ส่วนขยาย "Markdown Preview Mermaid Support" หรือ "Mermaid Editor"), Mermaid Live Editor (https://mermaid.live) หรือเครื่องมือ CLI `@mermaid-js/mermaid-cli`
- หากต้องการ Export ภาพใหม่หลังแก้ไข สามารถใช้คำสั่ง:
  ```
  npx @mermaid-js/mermaid-cli -i staysense-workflow.mmd -o staysense-workflow.svg -b white
  npx @mermaid-js/mermaid-cli -i staysense-workflow.mmd -o staysense-workflow.png -b white -w 3200
  ```
- แผนภาพนี้ไม่มีความสัมพันธ์แบบ `<<include>>` หรือ `<<extend>>` เนื่องจากเป็น Workflow Diagram ไม่ใช่ Use Case Diagram และไม่มีฟังก์ชันเจ้าของที่พักหรือการจองที่พักปรากฏอยู่ในแผนภาพ ตรงตามขอบเขตที่กำหนด
