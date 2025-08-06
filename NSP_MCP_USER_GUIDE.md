# NSP MCP Connector - Användarguide

## 🎯 **Översikt**

NSP MCP Connector ger dig enkla och kraftfulla funktioner för att arbeta med ärenden i NSP via Copilot Studio. Funktionerna är designade för att vara intuitiva och användarvänliga.

## 📋 **Ärendetyper och Statusar**

### **Ärendetyper:**
- **Ticket** - IT-ärenden
- **ServiceOrderRequest** - Service Order Requests  
- **Incident** - Incidenter

### **Statusar (övergripande tillstånd):**
- **New** - Nya ärenden
- **Registered** - Registrerade
- **Assigned** - Tilldelade
- **In progress** - Pågående
- **Pending** - Väntande
- **Resolved** - Lösda
- **Closed** - Stängda

### **Faser (workflow-stadium):**
- **New** - Nya
- **Open** - Öppna
- **Resolved** - Lösda
- **Closed** - Stängda

## 🚀 **Enkla Funktioner**

### **1. Mina ärenden**
```json
{
  "name": "get_my_tickets",
  "arguments": {
    "user_email": "användare@företag.se",
    "page": 1,
    "page_size": 15
  }
}
```
*Hämtar alla ärenden som är tilldelade till dig*

### **2. Öppna ärenden**
```json
{
  "name": "get_open_tickets",
  "arguments": {
    "page": 1,
    "page_size": 15
  }
}
```
*Hämtar alla ärenden som inte är stängda*

### **3. Stängda ärenden**
```json
{
  "name": "get_closed_tickets",
  "arguments": {
    "page": 1,
    "page_size": 15
  }
}
```
*Hämtar alla stängda ärenden*

### **4. Ärenden efter status**
```json
{
  "name": "get_tickets_by_status",
  "arguments": {
    "status": "In progress",
    "page": 1,
    "page_size": 15
  }
}
```
*Hämtar ärenden med specifik status*

### **5. Ärenden efter typ**
```json
{
  "name": "get_tickets_by_type",
  "arguments": {
    "entity_type": "Ticket",
    "page": 1,
    "page_size": 15
  }
}
```
*Hämtar ärenden av specifik typ*

### **6. Ärenden efter fas**
```json
{
  "name": "get_tickets_by_stage",
  "arguments": {
    "entity_type": "Ticket",
    "stage": "Open",
    "page": 1,
    "page_size": 15
  }
}
```
*Hämtar ärenden i specifik fas för en ärendetyp*

## 🔍 **Avancerad sökning**

### **Kombinerad sökning**
```json
{
  "name": "search_tickets",
  "arguments": {
    "status": "Assigned",
    "entity_type": "Ticket",
    "stage": "Open",
    "user_email": "användare@företag.se",
    "page": 1,
    "page_size": 15
  }
}
```
*Alla parametrar är valfria - kombinera efter behov*

## 💡 **Praktiska exempel**

### **Exempel 1: "Visa mina öppna ärenden"**
```json
{
  "name": "get_my_tickets",
  "arguments": {
    "user_email": "användare@företag.se"
  }
}
```

### **Exempel 2: "Visa alla pågående tickets"**
```json
{
  "name": "get_tickets_by_status",
  "arguments": {
    "status": "In progress"
  }
}
```

### **Exempel 3: "Visa öppna incidents"**
```json
{
  "name": "get_tickets_by_stage",
  "arguments": {
    "entity_type": "Incident",
    "stage": "Open"
  }
}
```

### **Exempel 4: "Visa alla tilldelade tickets som är öppna"**
```json
{
  "name": "search_tickets",
  "arguments": {
    "status": "Assigned",
    "entity_type": "Ticket",
    "stage": "Open"
  }
}
```

## 📊 **Svarformat**

Alla funktioner returnerar data i följande format:

```json
{
  "Result": [
    {
      "id": 12345,
      "title": "Ärendetitel",
      "type": "Ticket",
      "status": "Assigned",
      "stage": "Open",
      "assigned_to": "användare@företag.se",
      "created_date": "2024-01-15T10:30:00Z",
      "priority": "Medium",
      "description": "Beskrivning av ärendet..."
    }
  ],
  "TotalCount": 150,
  "filter_description": "Status: Assigned, Typ: Ticket"
}
```

## 🎯 **Rekommenderad användning**

### **För vanliga användare:**
1. **`get_my_tickets`** - Se dina egna ärenden
2. **`get_open_tickets`** - Se alla öppna ärenden
3. **`get_tickets_by_status`** - Filtrera på status

### **För avancerade användare:**
1. **`get_tickets_by_stage`** - Specifik fas-filtrering
2. **`search_tickets`** - Kombinerad sökning
3. **`get_tickets`** - Fullständig kontroll

## 🔧 **Tips för bästa användning**

1. **Börja enkelt** - Använd de enkla funktionerna först
2. **Kombinera filter** - Använd `search_tickets` för komplexa sökningar
3. **Använd paginering** - Sätt `page_size` till rimliga värden (15-50)
4. **Kontrollera filter** - Använd `filter_description` för att se vad som applicerats

## ❓ **Vanliga frågor**

**Q: Vad är skillnaden mellan status och fas?**
A: Status är övergripande tillstånd (t.ex. "Assigned"), fas är var i processen ärendet befinner sig (t.ex. "Open").

**Q: Kan jag söka på flera kriterier samtidigt?**
A: Ja, använd `search_tickets` funktionen med flera parametrar.

**Q: Vilka statusar finns tillgängliga?**
A: New, Registered, Assigned, In progress, Pending, Resolved, Closed.

**Q: Vilka faser finns för olika ärendetyper?**
A: Alla har New, Open, Resolved, Closed, men med olika ID:n. 