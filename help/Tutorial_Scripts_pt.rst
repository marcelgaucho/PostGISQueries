======================================
Documentação do plugin PostGIS Queries
======================================

Instalação
==========

Extraia o arquivo zip disponível em
https://github.com/marcelgaucho/PostGISQueries/releases para a pasta de
plugins do QGIS. Essa pasta pode ser acessada da seguinte maneira:

Menu Configurações → Perfis de Usuário → Abrir Pasta de Perfil Ativo

Uma pasta será aberta. Nela navegue até python/plugins.

Uso
===

Recomenda-se deixar a caixa do script aberta após a execução para, em
caso de possíveis problemas, saber a origem da falha. Primeiro vá em
Configurações → Opções… . Depois, na aba Processamento → Geral, marque a
opção *Manter a caixa de diálogo aberto após executar o algoritmo*.

O uso será demonstrado com um script, sendo semelhante para os demais. O
exemplo será do Script da Figura abaixo, usado para achar sobreposição
entre duas camadas.

-  Input Layer (connection): escolher qualquer camada do banco em que as
   camadas estão.

-  Table: Tabela que se refere à primeira camada. O nome precisa vir
   acompanhado do esquema. Por exemplo: bc250_base.hid_massa_dagua_a.

-  Table2: Tabela que se refere à segunda camada. nome precisa vir
   acompanhado do esquema. Por exemplo:
   bc250_base.lml_area_densamente_edificada_a.

-  Output Layer: é possível deixar vazio para salvar em um arquivo
   temporário. Caso o script dê alguma falha, tente resolver salvando a
   saída em um shapefile. Nos três pontos ao lado, escolha Salvar no
   arquivo…, altere o Tipo para SHP files (\*.shp), crie um nome para o
   arquivo e pressione Salvar.

-  Em alguns scripts, é pedido também a Primary Key (Chave primária). O
   valor padrão é id. Alteramos o valor se a chave primária da tabela
   possuir um nome diferente.
   
.. image:: fig0.jpg

Scripts disponíveis
===================

Find Dangles (Acha Dangles)
---------------------------

Acha dangles (pontas soltas) em uma camada de linhas.

Find Empty or NULL Geometries (Acha geometrias vazias ou nulas)
---------------------------------------------------------------

Acha geometrias vazias ou que estão preenchidas com NULL.

Find Endpoints that don’t touch polygon (Acha extremos que não encostam na fronteira do polígono)
-------------------------------------------------------------------------------------------------

Acha os extremos, pontos inicial e final de cada linha, referentes a uma
camada de linhas (Line Table) que não tocam a fronteira de uma camada de
polígonos (Polygon Table). Foi criada para achar pontes que não encostam
na fronteira da massa d’água.

Find Gaps (Acha lacunas)
------------------------

Criado para uma camada em que seus polígonos devem estar adjacentes,
como uma camada de limite estadual, municipal ou de países. Lacunas são
retornadas como polígonos.

Find Gaps (2) (Acha lacunas (2))
--------------------------------

Mesma função que o script *Acha lacunas*, entretanto isso é feito de
maneira distinta no código, o que pode ser mais lento ou mais rápido. As
lacunas são retornadas como linhas, sendo retornadas também as linhas de
fronteira onde não há polígono adjacente, como é o caso de ilhas e
limites na costa marítima.

Find Geometries Different From Other Layer (Acha geometrias diferentes de outra camada)
---------------------------------------------------------------------------------------

Acha geometrias presentes na primeira tabela (Table) que não são
exatamente iguais a alguma geometria da segunda tabela (Table2).

Find Geometries With Repeated Vertices (Acha geometrias com vértices repetidos)
-------------------------------------------------------------------------------

Retorna geometrias que contêm vértices repetidos.

Find Invalid Polygons (Acha polígonos inválidos)
------------------------------------------------

Acha polígonos inválidos segundo o PostGIS, que usa a OpenGIS Simple
Features Implementation Specification for SQL 1.1. Polígonos inválidos
são aqueles que contêm auto-interseção ou que os anéis possuem
sobreposição. Em caso de multipolígono, os polígonos que o constituem
precisam ser válidos e também não pode haver sobreposição entre eles,
sendo que devem se tocar no máximo em um número finito de pontos.

Segundo o PostGIS, entretanto, vértices duplicados são permitidos, não
sendo causa para a invalidade dos polígonos.

Find K Nearest Neighbors Whithin Distance (Acha K vizinhos mais próximos dentro de uma certa distância)
-------------------------------------------------------------------------------------------------------

Dado uma certa camada de entrada (Input Layer), detecta os K vizinhos
mais próximos que estão em uma camada de vizinhos (Neighbors Layer) e
dentro de uma certa distância. Os K vizinhos mais próximos são as K
feições da camada de vizinhos que estão mais próximas a uma feição da
camada de entrada e se encontram a uma certa distância (tolerância)
dessa feição.

A chave primária para as duas camadas precisa ser fornecida.

A tolerância (Tolerance) é o raio de busca limite. Vizinhos que estão
mais distantes que a tolerância não serão incluídos no resultado. O
número de vizinhos (Number of neighbors) se refere ao número K de
vizinhos mais próximos para ser encontrado.

Por exemplo, podemos achar os 3 aglomerados rurais isolados mais
próximos de cada trecho rodoviário, sendo que os aglomerados rurais
detectados devem estar dentro de 111 metros (0,001 grau). Nesse caso,
trecho rodoviário será a camada de entrada e aglomerado rural isolado
será a camada de vizinhos. O número de vizinhos K será 3 e a tolerância
será 0,001 grau. Isso significa que, para cada trecho rodoviário, serão
incluídos no resultado até 3 aglomerados, que serão os aglomerados mais
próximos a esse trecho e que estejam a uma distância de até 0,001 grau.

Find Not Simple Lines (Self-Intersection) (Acha linhas não-simples (Autointerseção))
------------------------------------------------------------------------------------

Acha linhas que não sejam simples. Linhas não-simples são caracterizadas
por conter uma auto-interseção. Isso quer dizer que a linha intercepta a
própria linha em um ponto que não é um dos extremos da linha. Os
extremos da linha são os pontos inicial e final.

É interessante notar que uma linha fechada, na qual o ponto final é
igual ao ponto inicial, é uma linha simples, pois o único lugar de
auto-interseção da linha é o ponto inicial, que é igual ao ponto final.

Uma multilinha é considerada simples se todas as linhas que a constituem
são simples e, além disso, elas não se tocam entre si em pontos que não
estão em seus extremos.

Find Overlap In One Layer (Acha sobreposição em uma camada)
-----------------------------------------------------------

Usado para detectar a sobreposição de polígonos em uma mesma camada,
como por exemplo de limites da unidade da federação.

Find Overlap In Two Layers (Acha sobreposição em duas camadas)
--------------------------------------------------------------

Usado para achar sobreposição entre polígonos de camadas distintas. Por
exemplo, entre área edificada e massa d’água.

Find polygons that aren’t filled by polygons from other layer (Acha polígonos que não são preenchidos por polígonos de outra camada)
------------------------------------------------------------------------------------------------------------------------------------

Acha partes de polígonos que não são preenchidos por polígonos de outra
camada. A tabela de polígonos externos (Outer Polygon Table) é a camada
cujos polígonos devem ser preenchidos por polígonos presentes na tabela
de polígonos internos (Inner Polygon Table).

São retornados partes dos polígonos externos que não são preenchidos por
polígonos internos, assim como a respectiva chave primária do polígono
externo. O nome do campo de chave primária da tabela de polígonos
externos (Outer Polygon Table Primary Key) também deve ser passado como
parâmetro.

Find Polygons that don’t contain 1 point (Acha polígonos que não contêm 1 ponto)
--------------------------------------------------------------------------------

Acha polígonos que não contém 1 ponto pertencente a uma outra camada de
pontos. Isto é, os polígonos não contêm nenhum ponto ou contêm mais de
um ponto.

Find Polygons with Holes (Acha polígonos com holes)
---------------------------------------------------

Acha polígonos que contêm holes. Pode ser útil para detectar polígonos
com holes em camadas de limites (estaduais, municipais, etc), onde pode
haver holes, mas é incomum que haja.

Find Pseudonodes (Acha pseudonós)
---------------------------------

Acha os pseudonós de uma camada tipo linha. Isso significa achar onde há
uma quebra da geometria, mas não ocorre uma interseção de linhas.

A tolerância (*tolerance*) é usada para sinalizar que dois extremos de
linhas distintas serão considerados como um nó se tiverem distância
menor que a tolerância. A tolerância padrão é 0,000001, o que equivale a
11 cm na Linha do Equador. A intenção de usar a tolerância é conseguir
uma detecção de pseudonós mesmo onde os extremos não estejam
perfeitamente aderentes no PostGIS. Apesar dos extremos cuja distância
seja menor que a tolerância serem considerados como um só nó na análise,
dois pontos relativos aos extremos serão retornados no resultado caso
eles não tiverem as mesmas coordenadas e sejam pseudonós.

O campo excluído (*excluded field*) é usado para sinalizar que linhas
adjacentes com atributos distintos deste campo não serão considerados
como pseudonós.

Find Repeated Geometries (Acha geometrias repetidas)
----------------------------------------------------

Acha geometrias duplicadas em uma camada.

Find Undershoot and Overshoot (Acha undershoot e overshoot)
-----------------------------------------------------------

Usado para achar undershoot e overshoot em uma camada de linhas. A
tolerância é o distanciamento máximo para detecção. Por exemplo, se a
distância de um dangle a outra linha for valor maior que a tolerância,
ele não será incluído no resultado. A unidade da tolerância depende do
sistema de coordenadas, sendo que a tolerância padrão está estipulada
como 0,0001, aproximadamente 11 metros no sistema de coordenadas
longitude e latitude SIRGAS 2000.

Return Geometry Without Holes (Retorna Geometria sem Holes)
-----------------------------------------------------------

Ela retornará a geometria de uma camada sem seus aneis interiores
(holes).
