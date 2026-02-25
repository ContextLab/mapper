#!/usr/bin/env python3
"""Generate 50 european-history questions and assemble domain file."""

import json
import hashlib
import random

# All 50 questions organized by difficulty level
questions = [
    # ==================== L1 (13 questions) ====================
    {
        "question_text": "What event began in 1789 when French citizens stormed the Bastille, leading to the overthrow of the monarchy and a radical restructuring of French society and government?",
        "correct_answer": "The French Revolution",
        "distractors": [
            "The Paris Commune uprising",
            "The July Revolution of 1830",
            "The Napoleonic Wars"
        ],
        "difficulty": 1,
        "source_article": "French Revolution",
        "domain_ids": ["european-history"],
        "concepts_tested": ["French Revolution"]
    },
    {
        "question_text": "Which global conflict, lasting from 1914 to 1918, was primarily fought in Europe and involved trench warfare, new weapons technology, and unprecedented casualties among major powers?",
        "correct_answer": "World War I",
        "distractors": [
            "World War II",
            "The Franco-Prussian War",
            "The Napoleonic Wars"
        ],
        "difficulty": 1,
        "source_article": "World War I",
        "domain_ids": ["european-history"],
        "concepts_tested": ["World War I"]
    },
    {
        "question_text": "What was the deadliest conflict in human history, lasting from 1939 to 1945, involving the Allied and Axis powers and resulting in the defeat of Nazi Germany and Imperial Japan?",
        "correct_answer": "World War II",
        "distractors": [
            "World War I",
            "The Seven Years' War",
            "The Thirty Years' War"
        ],
        "difficulty": 1,
        "source_article": "World War II",
        "domain_ids": ["european-history"],
        "concepts_tested": ["World War II"]
    },
    {
        "question_text": "What ancient civilization dominated the Mediterranean for centuries from its capital on the Italian Peninsula, building roads, aqueducts, and a legal system that influenced Western civilization?",
        "correct_answer": "The Roman Empire",
        "distractors": [
            "The Byzantine Empire",
            "The Carthaginian Empire",
            "The Macedonian Empire"
        ],
        "difficulty": 1,
        "source_article": "Roman Empire",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Roman Empire"]
    },
    {
        "question_text": "What 14th-century pandemic, caused by the bacterium Yersinia pestis, killed an estimated one-third of Europe's population between 1347 and 1353?",
        "correct_answer": "The Black Death",
        "distractors": [
            "The Great Plague of London",
            "The Antonine Plague",
            "The Plague of Justinian"
        ],
        "difficulty": 1,
        "source_article": "Black Death",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Black Death"]
    },
    {
        "question_text": "What cultural and intellectual movement, originating in Italy around the 14th century, emphasized classical learning, humanism, and artistic innovation, marking the transition from the medieval to the modern era?",
        "correct_answer": "The Renaissance",
        "distractors": [
            "The Enlightenment",
            "The Baroque period",
            "The Romantic movement"
        ],
        "difficulty": 1,
        "source_article": "Renaissance",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Renaissance"]
    },
    {
        "question_text": "Which French military leader rose to power during the Revolution, crowned himself Emperor in 1804, and conquered much of Europe before his final defeat at Waterloo in 1815?",
        "correct_answer": "Napoleon Bonaparte",
        "distractors": [
            "Louis XIV of France",
            "Charles de Gaulle",
            "Maximilien Robespierre"
        ],
        "difficulty": 1,
        "source_article": "Napoleon",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Napoleon Bonaparte"]
    },
    {
        "question_text": "What term refers to the systematic, state-sponsored genocide of six million Jews by Nazi Germany and its collaborators during World War II?",
        "correct_answer": "The Holocaust",
        "distractors": [
            "The Armenian Genocide",
            "The Rwandan Genocide",
            "The Bosnian Genocide"
        ],
        "difficulty": 1,
        "source_article": "The Holocaust",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Holocaust"]
    },
    {
        "question_text": "What term describes the geopolitical tension between the United States and Soviet Union from roughly 1947 to 1991, characterized by nuclear arms races, proxy wars, and ideological rivalry?",
        "correct_answer": "The Cold War",
        "distractors": [
            "The Great Game",
            "The Space Race",
            "The Iron Curtain"
        ],
        "difficulty": 1,
        "source_article": "Cold War",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Cold War"]
    },
    {
        "question_text": "Which ancient civilization, centered on the Aegean Sea, is credited with developing democracy, Western philosophy, and the Olympic Games, with city-states like Athens and Sparta?",
        "correct_answer": "Ancient Greece",
        "distractors": [
            "Ancient Egypt",
            "Ancient Persia",
            "Ancient Phoenicia"
        ],
        "difficulty": 1,
        "source_article": "Ancient Greece",
        "domain_ids": ["european-history"],
        "concepts_tested": ["ancient Greece"]
    },
    {
        "question_text": "What 16th-century religious movement, initiated by Martin Luther's Ninety-Five Theses in 1517, challenged Catholic Church authority and led to the creation of Protestant denominations across Europe?",
        "correct_answer": "The Protestant Reformation",
        "distractors": [
            "The Counter-Reformation",
            "The Great Schism of 1054",
            "The English Reformation"
        ],
        "difficulty": 1,
        "source_article": "Reformation",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Protestant Reformation"]
    },
    {
        "question_text": "What iconic event occurred on November 9, 1989, when East German authorities opened border crossings, allowing citizens to freely cross into West Berlin and symbolically ending the Cold War division of Europe?",
        "correct_answer": "The fall of the Berlin Wall",
        "distractors": [
            "German reunification under the Two Plus Four Treaty",
            "The dissolution of the Soviet Union",
            "The Velvet Revolution in Czechoslovakia"
        ],
        "difficulty": 1,
        "source_article": "Fall of the Berlin Wall",
        "domain_ids": ["european-history"],
        "concepts_tested": ["fall of the Berlin Wall"]
    },
    {
        "question_text": "What series of religious wars, launched by Western European Christians from the late 11th to the 13th century, aimed to recapture the Holy Land from Muslim control?",
        "correct_answer": "The Crusades",
        "distractors": [
            "The Reconquista",
            "The Northern Crusades",
            "The Wars of Religion"
        ],
        "difficulty": 1,
        "source_article": "Crusades",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Crusades"]
    },

    # ==================== L2 (13 questions) ====================
    {
        "question_text": "What 1814-1815 diplomatic assembly, led by Metternich, Castlereagh, and Talleyrand, redrew the map of Europe after Napoleon's defeat and established a conservative balance-of-power order?",
        "correct_answer": "The Congress of Vienna",
        "distractors": [
            "The Treaty of Versailles conference",
            "The Concert of Europe summit",
            "The Peace of Westphalia negotiations"
        ],
        "difficulty": 2,
        "source_article": "Congress of Vienna",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Congress of Vienna"]
    },
    {
        "question_text": "What devastating 1618-1648 conflict began as a religious struggle between Protestants and Catholics in the Holy Roman Empire but evolved into a broader European power struggle?",
        "correct_answer": "The Thirty Years' War",
        "distractors": [
            "The Hundred Years' War",
            "The Wars of the Roses",
            "The Seven Years' War"
        ],
        "difficulty": 2,
        "source_article": "Thirty Years' War",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Thirty Years' War"]
    },
    {
        "question_text": "What 1215 charter, sealed by King John of England under pressure from rebellious barons, established the principle that the monarch was subject to the rule of law?",
        "correct_answer": "The Magna Carta",
        "distractors": [
            "The English Bill of Rights",
            "The Petition of Right",
            "The Provisions of Oxford"
        ],
        "difficulty": 2,
        "source_article": "Magna Carta",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Magna Carta"]
    },
    {
        "question_text": "What period, spanning roughly the 15th to 17th centuries, saw European powers like Portugal and Spain undertake maritime voyages that established global trade routes and colonial empires?",
        "correct_answer": "The Age of Exploration",
        "distractors": [
            "The Commercial Revolution",
            "The Columbian Exchange era",
            "The Age of Imperialism"
        ],
        "difficulty": 2,
        "source_article": "Age of Discovery",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Age of Exploration"]
    },
    {
        "question_text": "What 18th-century intellectual movement, associated with thinkers like Voltaire, Locke, and Kant, championed reason, science, and individual rights as foundations for society and government?",
        "correct_answer": "The Enlightenment",
        "distractors": [
            "The Renaissance",
            "The Romantic movement",
            "The Scientific Revolution"
        ],
        "difficulty": 2,
        "source_article": "Age of Enlightenment",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Enlightenment"]
    },
    {
        "question_text": "Which Prussian statesman unified the German states into a single empire in 1871 through a strategy of diplomacy and military force known as \"blood and iron\"?",
        "correct_answer": "Otto von Bismarck",
        "distractors": [
            "Frederick the Great",
            "Kaiser Wilhelm II",
            "Helmuth von Moltke"
        ],
        "difficulty": 2,
        "source_article": "Otto von Bismarck",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Otto von Bismarck"]
    },
    {
        "question_text": "What was the eastern continuation of the Roman Empire, with its capital at Constantinople, that preserved Greco-Roman culture and Orthodox Christianity until its fall to the Ottomans in 1453?",
        "correct_answer": "The Byzantine Empire",
        "distractors": [
            "The Holy Roman Empire",
            "The Latin Empire",
            "The Ottoman Empire"
        ],
        "difficulty": 2,
        "source_article": "Byzantine Empire",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Byzantine Empire"]
    },
    {
        "question_text": "What 1919 peace agreement formally ended World War I, imposed heavy reparations and territorial losses on Germany, and is widely seen as contributing to the rise of Nazism?",
        "correct_answer": "The Treaty of Versailles",
        "distractors": [
            "The Treaty of Brest-Litovsk",
            "The Treaty of Trianon",
            "The Armistice of November 1918"
        ],
        "difficulty": 2,
        "source_article": "Treaty of Versailles",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Treaty of Versailles"]
    },
    {
        "question_text": "What prolonged 1337-1453 dynastic conflict between England and France featured battles like Crecy and Agincourt and the rise of Joan of Arc?",
        "correct_answer": "The Hundred Years' War",
        "distractors": [
            "The Thirty Years' War",
            "The Wars of the Roses",
            "The Anglo-French Wars"
        ],
        "difficulty": 2,
        "source_article": "Hundred Years' War",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Hundred Years' War"]
    },
    {
        "question_text": "What medieval social and economic system organized European society around a hierarchy of lords granting land (fiefs) to vassals in exchange for military service and labor?",
        "correct_answer": "Feudalism",
        "distractors": [
            "Manorialism",
            "Mercantilism",
            "Serfdom"
        ],
        "difficulty": 2,
        "source_article": "Feudalism",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Feudalism"]
    },
    {
        "question_text": "What 1917 series of upheavals overthrew the Romanov dynasty and ultimately brought the Bolsheviks under Lenin to power, creating the world's first communist state?",
        "correct_answer": "The Russian Revolution",
        "distractors": [
            "The Decembrist revolt",
            "The February Revolution alone",
            "The Russian Civil War"
        ],
        "difficulty": 2,
        "source_article": "Russian Revolution",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Russian Revolution"]
    },
    {
        "question_text": "What 431-404 BC conflict between Athens and Sparta, chronicled by Thucydides, ended Athenian dominance and reshaped the political order of the ancient Greek world?",
        "correct_answer": "The Peloponnesian War",
        "distractors": [
            "The Greco-Persian Wars",
            "The Corinthian War",
            "The Lamian War"
        ],
        "difficulty": 2,
        "source_article": "Peloponnesian War",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Peloponnesian War"]
    },
    {
        "question_text": "What term describes the practice by which European powers established political control over territories in Africa, Asia, and the Americas from the 15th century onward, extracting resources and imposing cultural systems?",
        "correct_answer": "Colonialism",
        "distractors": [
            "Imperialism",
            "Mercantilism",
            "Globalization"
        ],
        "difficulty": 2,
        "source_article": "Colonialism",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Colonialism"]
    },

    # ==================== L3 (12 questions) ====================
    {
        "question_text": "The Peace of Westphalia (1648) is often cited by international relations scholars as establishing a foundational principle of the modern state system. What is that principle?",
        "correct_answer": "State sovereignty, meaning each state has exclusive authority over its own territory without external interference",
        "distractors": [
            "Collective security, meaning states are obligated to jointly defend any member attacked by an aggressor",
            "Balance of power, meaning no single state should be allowed to dominate the European continent",
            "Freedom of navigation, meaning all states have equal access to international waterways and trade routes"
        ],
        "difficulty": 3,
        "source_article": "Peace of Westphalia",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Peace of Westphalia"]
    },
    {
        "question_text": "The Concert of Europe maintained relative peace among great powers for decades after 1815. Which mechanism was central to this system's functioning?",
        "correct_answer": "Regular multilateral congresses where great powers collectively managed crises and territorial disputes through diplomacy",
        "distractors": [
            "A standing multinational army that enforced borders and suppressed revolutionary movements across the continent",
            "Binding mutual defense treaties requiring all signatories to declare war if any member was attacked",
            "An international court with authority to adjudicate disputes and impose legally binding rulings on states"
        ],
        "difficulty": 3,
        "source_article": "Concert of Europe",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Concert of Europe"]
    },
    {
        "question_text": "How did the English enclosure movement most directly contribute to the Industrial Revolution?",
        "correct_answer": "It displaced rural peasants from common lands, creating a large wage-labor force that migrated to urban factories",
        "distractors": [
            "It generated tax revenue from enclosed estates that Parliament invested directly into factory construction",
            "It introduced mechanized plowing techniques that were later adapted for use in textile manufacturing",
            "It concentrated livestock breeding programs that produced the horses needed to power early industrial machinery"
        ],
        "difficulty": 3,
        "source_article": "Enclosure",
        "domain_ids": ["european-history"],
        "concepts_tested": ["enclosure movement"]
    },
    {
        "question_text": "Why did the Revolutions of 1848 ultimately fail to achieve lasting political change in most European countries despite their initial widespread success?",
        "correct_answer": "Liberal and nationalist factions fragmented over competing goals, allowing conservative forces to regroup and reassert monarchical authority",
        "distractors": [
            "Foreign military intervention by Russia and Britain crushed every revolutionary government before they could consolidate power",
            "Widespread famine and cholera epidemics weakened revolutionary armies, forcing them to surrender to royalist forces",
            "Revolutionary leaders voluntarily restored the old monarchies after negotiating constitutional concessions that were later honored"
        ],
        "difficulty": 3,
        "source_article": "Revolutions of 1848",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Revolutions of 1848"]
    },
    {
        "question_text": "What lasting institutional legacy did Charlemagne's Carolingian Empire establish that shaped medieval Western European governance and culture?",
        "correct_answer": "A partnership between Frankish royal authority and the Roman papacy that defined church-state relations throughout the medieval period",
        "distractors": [
            "A feudal parliament system where elected representatives from each province voted on imperial taxation and military policy",
            "A standardized legal code derived from Roman law that replaced all local customs across Western and Central Europe",
            "A permanent standing army recruited from all social classes that defended the empire's borders for the next three centuries"
        ],
        "difficulty": 3,
        "source_article": "Carolingian Empire",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Carolingian Empire"]
    },
    {
        "question_text": "The Dreyfus Affair divided France into opposing camps in the 1890s. What broader political consequence did it have for French society?",
        "correct_answer": "It galvanized republican and secular forces to pass laws separating church and state and curbing the political influence of the army",
        "distractors": [
            "It led France to abandon its colonial empire in North Africa as public opinion turned against military adventurism abroad",
            "It triggered a military coup that replaced the Third Republic with a constitutional monarchy under the Orleans dynasty",
            "It prompted France to form an immediate military alliance with Germany to prevent future internal political manipulation"
        ],
        "difficulty": 3,
        "source_article": "Dreyfus affair",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Dreyfus Affair"]
    },
    {
        "question_text": "The Eastern Question dominated European diplomacy throughout the 19th century. What was the core dilemma that the great powers faced?",
        "correct_answer": "How to manage the decline of the Ottoman Empire without triggering a major war over control of its former territories",
        "distractors": [
            "How to prevent Russia from industrializing rapidly enough to challenge British naval supremacy in the Mediterranean",
            "How to integrate the newly independent Balkan states into the Concert of Europe as equal sovereign members",
            "How to suppress nationalist uprisings in Eastern Europe without provoking intervention from the United States"
        ],
        "difficulty": 3,
        "source_article": "Eastern Question",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Eastern Question"]
    },
    {
        "question_text": "What specific economic crisis fatally undermined the Weimar Republic's democratic legitimacy and created conditions for the Nazi rise to power?",
        "correct_answer": "The Great Depression caused mass unemployment, which radicalized voters toward extremist parties promising economic recovery",
        "distractors": [
            "The 1923 hyperinflation permanently destroyed public savings, making democratic governance impossible for the next decade",
            "British and French trade blockades after 1929 starved Germany of raw materials, collapsing its export economy entirely",
            "The Dawes Plan's sudden cancellation in 1928 forced Germany to immediately repay all remaining World War I reparations"
        ],
        "difficulty": 3,
        "source_article": "Weimar Republic",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Weimar Republic"]
    },
    {
        "question_text": "What was the primary economic function of the Hanseatic League in medieval Northern Europe?",
        "correct_answer": "A commercial confederation of merchant guilds and trading towns that secured trade privileges and monopolies across the Baltic and North Sea regions",
        "distractors": [
            "A royal banking consortium that financed monarchs' wars in exchange for exclusive rights to collect customs duties at all ports",
            "A religious trade network run by monastic orders that controlled the production and distribution of agricultural goods across Europe",
            "A military alliance of coastal cities that maintained a permanent navy to protect Mediterranean shipping lanes from piracy"
        ],
        "difficulty": 3,
        "source_article": "Hanseatic League",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Hanseatic League"]
    },
    {
        "question_text": "What distinguished the Spanish Inquisition's primary targets and methods from earlier medieval inquisitions?",
        "correct_answer": "It focused on conversos and moriscos suspected of secretly practicing Judaism or Islam, operating under royal rather than papal authority",
        "distractors": [
            "It targeted Protestant reformers spreading Lutheran doctrines across Iberia, operating as an arm of the papal curia in Rome",
            "It prosecuted accused witches using systematic torture trials, functioning independently of both royal and ecclesiastical oversight",
            "It investigated corrupt clergy who sold indulgences fraudulently, acting under joint authority of the pope and Spanish parliament"
        ],
        "difficulty": 3,
        "source_article": "Spanish Inquisition",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Spanish Inquisition"]
    },
    {
        "question_text": "What was the significance of the 1884-1885 Berlin Conference in the context of the Scramble for Africa?",
        "correct_answer": "It established rules for European powers to claim African territory, requiring effective occupation rather than mere exploration or treaties",
        "distractors": [
            "It divided Africa into equal portions among European powers using geometric boundaries drawn along lines of latitude and longitude",
            "It granted exclusive colonial rights in Africa to Britain and France while banning Germany and Italy from territorial expansion",
            "It created an international administration to govern Africa jointly, with profits from resource extraction shared among all European nations"
        ],
        "difficulty": 3,
        "source_article": "Scramble for Africa",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Scramble for Africa"]
    },
    {
        "question_text": "What political vision motivated the Decembrist officers who revolted in Russia in December 1825, and why did their uprising fail?",
        "correct_answer": "They sought a constitutional monarchy or republic inspired by Western liberalism, but failed due to poor coordination and lack of popular support",
        "distractors": [
            "They demanded the abolition of serfdom and redistribution of noble lands, but failed because peasant armies refused to join them",
            "They wanted to restore the old Muscovite tsardom and reject Western reforms, but failed when the army remained loyal to the tsar",
            "They aimed to establish a military dictatorship modeled on Napoleonic France, but failed when Britain intervened diplomatically"
        ],
        "difficulty": 3,
        "source_article": "Decembrist revolt",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Decembrist revolt"]
    },

    # ==================== L4 (12 questions) ====================
    {
        "question_text": "Diocletian's administrative reforms fundamentally restructured the Roman Empire. What was the tetrarchy system he established, and what problem was it designed to solve?",
        "correct_answer": "A system of four co-emperors (two senior Augusti and two junior Caesares) governing different regions, designed to prevent civil wars over imperial succession",
        "distractors": [
            "A system of four senatorial councils each governing a province independently, designed to prevent military commanders from seizing the throne",
            "A system of four hereditary dynasties rotating imperial authority every decade, designed to prevent any single family from monopolizing power",
            "A system of four military districts each commanded by an elected general, designed to prevent barbarian invasions along the frontier"
        ],
        "difficulty": 4,
        "source_article": "Diocletian",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Diocletianic reforms"]
    },
    {
        "question_text": "The Investiture Controversy between Pope Gregory VII and Emperor Henry IV centered on a specific institutional power. What was it, and how was it resolved?",
        "correct_answer": "The right to appoint bishops and abbots; the 1122 Concordat of Worms compromised by separating spiritual investiture (papal) from temporal investiture (imperial)",
        "distractors": [
            "The right to levy taxes on church property; the 1122 Concordat of Worms gave the pope sole taxation authority over all ecclesiastical lands",
            "The right to call ecumenical councils; the 1122 Concordat of Worms granted the emperor authority to convene councils with papal approval",
            "The right to excommunicate secular rulers; the 1122 Concordat of Worms restricted excommunication to cases approved by both pope and emperor"
        ],
        "difficulty": 4,
        "source_article": "Investiture Controversy",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Investiture Controversy"]
    },
    {
        "question_text": "The Annales school transformed historical methodology in the 20th century. What was its central methodological innovation that distinguished it from traditional historiography?",
        "correct_answer": "Emphasizing long-duration social, economic, and geographic structures (the longue duree) over narrative accounts of political events and individual actors",
        "distractors": [
            "Applying Marxist class-struggle analysis systematically to all historical periods, rejecting any role for individual agency or cultural factors",
            "Using exclusively quantitative statistical methods borrowed from economics to measure historical change, rejecting qualitative evidence entirely",
            "Focusing on oral history and ethnographic fieldwork among living populations to reconstruct past societies, rejecting archival documents"
        ],
        "difficulty": 4,
        "source_article": "Annales school",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Annales school"]
    },
    {
        "question_text": "The Stab-in-the-back myth (Dolchstosslegende) served a specific political function in Weimar Germany. What false claim did it make, and which groups did it blame?",
        "correct_answer": "It claimed the German army was undefeated in the field but betrayed by civilian politicians, Jews, and Marxists who undermined the home front",
        "distractors": [
            "It claimed the Treaty of Versailles was illegally signed by rogue diplomats without military consent, blaming Allied-sympathizing bureaucrats",
            "It claimed German generals deliberately lost the war to preserve their estates, blaming the Prussian aristocracy and the Kaiser personally",
            "It claimed Allied propaganda caused German soldiers to desert en masse, blaming British intelligence services and French media operations"
        ],
        "difficulty": 4,
        "source_article": "Stab-in-the-back myth",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Stab-in-the-back myth"]
    },
    {
        "question_text": "What is translatio imperii, and how did medieval rulers use this concept to legitimize their authority?",
        "correct_answer": "The doctrine that supreme imperial authority transferred successively from ancient empires to their successors, used by Holy Roman Emperors to claim continuity with Rome",
        "distractors": [
            "The doctrine that papal authority superseded all secular power, used by medieval popes to claim the right to depose any European monarch",
            "The doctrine that military conquest automatically conferred legitimate sovereignty, used by Crusader kings to justify rule over conquered territories",
            "The doctrine that royal bloodlines carried divine authority through hereditary succession, used by French kings to deny papal interference in governance"
        ],
        "difficulty": 4,
        "source_article": "Translatio imperii",
        "domain_ids": ["european-history"],
        "concepts_tested": ["translatio imperii"]
    },
    {
        "question_text": "During the July Crisis of 1914, what specific role did the \"blank cheque\" assurance play in escalating a regional crisis into a continental war?",
        "correct_answer": "Germany's unconditional pledge of support to Austria-Hungary emboldened Vienna to issue an ultimatum to Serbia so harsh that it guaranteed Russian intervention",
        "distractors": [
            "Britain's secret guarantee to France triggered automatic mobilization across Western Europe once Germany declared war on Russia",
            "Russia's unconditional pledge to Serbia forced France to mobilize immediately, which activated the Franco-Russian military convention against Germany",
            "Austria-Hungary's unconditional pledge to the Ottoman Empire drew the Eastern Mediterranean into the conflict before Western powers could mediate"
        ],
        "difficulty": 4,
        "source_article": "July Crisis",
        "domain_ids": ["european-history"],
        "concepts_tested": ["July Crisis of 1914"]
    },
    {
        "question_text": "The Gracchi brothers attempted agrarian reform in the late Roman Republic. What specific law did Tiberius Gracchus propose, and how did the Senate respond?",
        "correct_answer": "He proposed enforcing the legal limit on public land holdings and redistributing excess land to landless citizens; the Senate incited a mob that killed him",
        "distractors": [
            "He proposed abolishing all private land ownership and creating collective farms; the Senate exiled him to Greece where he died in obscurity",
            "He proposed granting full Roman citizenship to all Italian allies with land grants; the Senate had him tried for treason and publicly executed",
            "He proposed taxing large estates to fund grain distributions to the urban poor; the Senate passed a competing law that made his reforms irrelevant"
        ],
        "difficulty": 4,
        "source_article": "Gracchi",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Gracchi reforms"]
    },
    {
        "question_text": "What political shift occurred during the Thermidorian Reaction of 1794, and how did it change the trajectory of the French Revolution?",
        "correct_answer": "The Convention overthrew and executed Robespierre, ending the Reign of Terror and shifting power to moderate republicans who dismantled the radical Jacobin apparatus",
        "distractors": [
            "The Girondins regained control of the Convention and restored the constitutional monarchy, ending the republican phase of the Revolution entirely",
            "Napoleon seized power in a military coup against the Directory, establishing the Consulate and ending the revolutionary period immediately",
            "The sans-culottes stormed the Convention and imposed direct democracy, eliminating all representative institutions until the army restored order"
        ],
        "difficulty": 4,
        "source_article": "Thermidorian Reaction",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Thermidorian Reaction"]
    },
    {
        "question_text": "What was the central intellectual dispute in the Querelle des Anciens et des Modernes, and which side ultimately prevailed in shaping Enlightenment thought?",
        "correct_answer": "Whether modern culture and literature could surpass classical antiquity; the Modernes' argument for progress prevailed, underpinning Enlightenment faith in human advancement",
        "distractors": [
            "Whether religious authority or secular reason should govern artistic production; the Anciens' defense of sacred art prevailed, shaping Baroque aesthetics",
            "Whether French or Italian should be the language of European scholarship; the Modernes' advocacy for French prevailed, displacing Latin in academies",
            "Whether empirical science or classical philosophy was more reliable; the Anciens' defense of Aristotelian logic prevailed, delaying the Scientific Revolution"
        ],
        "difficulty": 4,
        "source_article": "Quarrel of the Ancients and the Moderns",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Querelle des Anciens et des Modernes"]
    },
    {
        "question_text": "How did the Eastern Front in World War I differ strategically from the Western Front, and what was its decisive political consequence?",
        "correct_answer": "It featured mobile warfare across vast distances rather than static trenches, and its immense casualties and hardships precipitated the Russian Revolution of 1917",
        "distractors": [
            "It featured naval warfare across the Baltic Sea rather than land battles, and its outcome forced the Ottoman Empire to surrender in 1916",
            "It featured guerrilla warfare by partisan forces rather than conventional armies, and its stalemate led to the permanent partition of Poland",
            "It featured aerial bombing campaigns rather than infantry assaults, and its destruction of infrastructure caused Austria-Hungary to seek peace in 1915"
        ],
        "difficulty": 4,
        "source_article": "Eastern Front (World War I)",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Eastern Front (World War I)"]
    },
    {
        "question_text": "What were the specific territorial provisions of the 1916 Sykes-Picot Agreement, and why did it become a source of lasting controversy?",
        "correct_answer": "It secretly divided Ottoman Arab provinces into British and French spheres of influence, contradicting promises of Arab independence made to Sharif Hussein of Mecca",
        "distractors": [
            "It openly partitioned the entire Ottoman Empire among all Allied powers including Russia, contradicting Wilson's Fourteen Points on self-determination",
            "It secretly granted Palestine exclusively to France while giving Britain control of Egypt, contradicting the later Balfour Declaration's commitments",
            "It divided North Africa between Britain and Italy while excluding France, contradicting previous treaties guaranteeing French control of Algeria and Tunisia"
        ],
        "difficulty": 4,
        "source_article": "Sykes\u2013Picot Agreement",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Sykes-Picot Agreement"]
    },
    {
        "question_text": "What is the Pirenne thesis, and how does it challenge the traditional periodization of the end of the ancient world?",
        "correct_answer": "Henri Pirenne argued that Islamic conquests, not Germanic invasions, ended Mediterranean unity and created medieval Europe by cutting off Western trade routes in the 7th-8th centuries",
        "distractors": [
            "Henri Pirenne argued that Christianity, not barbarian invasions, ended classical culture by suppressing pagan learning and closing philosophical schools in the 4th century",
            "Henri Pirenne argued that climate change, not political collapse, ended ancient civilization by causing widespread crop failures across the Mediterranean in the 5th century",
            "Henri Pirenne argued that Roman economic decline, not external invasions, ended the ancient world through hyperinflation and the collapse of the gold standard in the 3rd century"
        ],
        "difficulty": 4,
        "source_article": "Pirenne thesis",
        "domain_ids": ["european-history"],
        "concepts_tested": ["Pirenne thesis"]
    }
]

# Write the questions file
with open("/Users/jmanning/mapper/data/domains/.working/european-history-questions.json", "w") as f:
    json.dump(questions, f, indent=2)

print(f"Wrote {len(questions)} questions to european-history-questions.json")

# Now assemble the final domain file
# Read existing domain file
with open("/Users/jmanning/mapper/data/domains/european-history.json", "r") as f:
    domain_data = json.load(f)

# Generate IDs and randomize answer slots
random.seed(42)

assembled_questions = []
for q in questions:
    # Generate ID: first 16 hex chars of SHA-256 of question_text
    qid = hashlib.sha256(q["question_text"].encode("utf-8")).hexdigest()[:16]

    # Collect all 4 options
    correct = q["correct_answer"]
    all_options = [correct] + q["distractors"]

    # Randomly assign to A/B/C/D slots
    random.shuffle(all_options)

    # Find which slot got the correct answer
    slots = ["A", "B", "C", "D"]
    correct_slot = slots[all_options.index(correct)]

    assembled_q = {
        "id": qid,
        "question_text": q["question_text"],
        "options": {
            "A": all_options[0],
            "B": all_options[1],
            "C": all_options[2],
            "D": all_options[3]
        },
        "correct_answer": correct_slot,
        "difficulty": q["difficulty"],
        "source_article": q["source_article"],
        "domain_ids": q["domain_ids"],
        "concepts_tested": q["concepts_tested"]
    }
    assembled_questions.append(assembled_q)

# Build final domain file
domain_data["questions"] = assembled_questions

with open("/Users/jmanning/mapper/data/domains/european-history.json", "w") as f:
    json.dump(domain_data, f, indent=2)

print(f"Wrote {len(assembled_questions)} assembled questions to european-history.json")

# Print summary
difficulty_counts = {}
for q in assembled_questions:
    d = q["difficulty"]
    difficulty_counts[d] = difficulty_counts.get(d, 0) + 1

print(f"\nDifficulty distribution:")
for d in sorted(difficulty_counts.keys()):
    print(f"  L{d}: {difficulty_counts[d]} questions")

# Verify IDs are unique
ids = [q["id"] for q in assembled_questions]
print(f"\nUnique IDs: {len(set(ids))}/{len(ids)}")

# Verify correct answer distribution
answer_counts = {}
for q in assembled_questions:
    a = q["correct_answer"]
    answer_counts[a] = answer_counts.get(a, 0) + 1
print(f"Answer distribution: {answer_counts}")
